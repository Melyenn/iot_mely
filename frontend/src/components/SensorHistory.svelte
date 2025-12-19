<script lang="ts">
	import LineChart from './LineChart.svelte'
	import CholeskySolver, { type Matrix } from '../utils/ringe-regression'

	type SensorData = {
		id: number
		timestamp: Date
		temperature: number
		gas: number
	}

	type Props = {
		sensorData: SensorData[]
	}

	let { sensorData }: Props = $props()

	let activeTab: 'temp' | 'gas' | 'all' = $state('all')

	// Cholesky solver state
	// Features: temp[t..t-9] (10) + gas[t..t-9] (10) + bias (1) = 21 features
	// Outputs: temp[t+1], gas[t+1] = 2 outputs
	const NUM_FEATURES = 21
	const NUM_OUTPUTS = 2
	const LOOKBACK = 10
	const PREDICTION_COUNT = 5
	const LAMBDA = 0.001

	let solver = CholeskySolver.init(NUM_FEATURES, NUM_OUTPUTS, LAMBDA)
	let lastLength = 0
	let weights: Matrix | null = $state(null)

	// Prediction state
	let predictedTemp = $state<number[]>([])
	let predictedGas = $state<number[]>([])

	// Build feature vector from temperature and gas arrays ending at index endIdx
	function buildFeatures(temps: number[], gases: number[], endIdx: number): Float64Array | null {
		if (endIdx < LOOKBACK - 1) return null // Not enough data

		const features = new Float64Array(NUM_FEATURES)
		let idx = 0

		for (let i = 0; i < LOOKBACK; i++) {
			features[idx++] = temps[endIdx - i]
		}

		for (let i = 0; i < LOOKBACK; i++) {
			features[idx++] = gases[endIdx - i]
		}

		// Bias
		features[idx] = 1

		return features
	}

	// Predict using weights matrix
	function predict(features: Float64Array, w: Matrix): { temp: number; gas: number } {
		let temp = 0
		let gas = 0
		for (let j = 0; j < NUM_FEATURES; j++) {
			temp += w[0][j] * features[j]
			gas += w[1][j] * features[j]
		}
		temp = Math.round(temp)
		gas = Math.round(gas)
		return { temp, gas }
	}

	// Perform inference: predict next 5 entries
	function performInference(temps: number[], gases: number[], w: Matrix): void {
		if (temps.length < LOOKBACK) {
			predictedTemp = []
			predictedGas = []
			return
		}

		const predTemps: number[] = []
		const predGases: number[] = []

		const tempWindow = temps.slice(-LOOKBACK)
		const gasWindow = gases.slice(-LOOKBACK)

		const features = new Float64Array(NUM_FEATURES)
		for (let i = 0; i < PREDICTION_COUNT; i++) {
			let idx = 0

			for (let j = 0; j < LOOKBACK; j++) {
				features[idx++] = tempWindow[LOOKBACK - 1 - j]
			}

			for (let j = 0; j < LOOKBACK; j++) {
				features[idx++] = gasWindow[LOOKBACK - 1 - j]
			}

			features[idx] = 1
			const pred = predict(features, w)
			predTemps.push(pred.temp)
			predGases.push(pred.gas)

			tempWindow.shift()
			tempWindow.push(pred.temp)

			gasWindow.shift()
			gasWindow.push(pred.gas)
		}

		predictedTemp = predTemps
		predictedGas = predGases
	}

	const tempData = $derived(sensorData.map(item => item.temperature).slice(-20))

	const gasData = $derived(sensorData.map(item => item.gas).slice(-20))

	const timeData = $derived(
		sensorData.map(item => item.timestamp.toLocaleTimeString()).slice(-20),
	)

	const avgTimeInterval = $derived.by(() => {
		const timestamps = sensorData.slice(-10).map(item => item.timestamp.getTime())

		if (timestamps.length < 2) return 3000 // Default 3 seconds if not enough data

		let totalInterval = 0
		for (let i = 1; i < timestamps.length; i++) {
			totalInterval += timestamps[i] - timestamps[i - 1]
		}
		return totalInterval / (timestamps.length - 1)
	})

	const extrapolatedTimeData = $derived.by(() => {
		if (sensorData.length === 0 || predictedTemp.length === 0) return []

		const lastTimestamp = sensorData[sensorData.length - 1]?.timestamp?.getTime()
		if (!lastTimestamp) return predictedTemp.map((_, i) => `+${i + 1}`)

		return predictedTemp.map((_, i) => {
			const futureTime = new Date(lastTimestamp + avgTimeInterval * (i + 1))
			return futureTime.toLocaleTimeString()
		})
	})

	const extendedTimeData = $derived([...timeData, ...extrapolatedTimeData])

	const predictedTempSeries = $derived([
		...Array(Math.max(0, tempData.length - 1)).fill(null),
		...(tempData.length > 0 ? [tempData[tempData.length - 1]] : []),
		...predictedTemp,
	])

	const predictedGasSeries = $derived([
		...Array(Math.max(0, gasData.length - 1)).fill(null),
		...(gasData.length > 0 ? [gasData[gasData.length - 1]] : []),
		...predictedGas,
	])

	const extendedTempData = $derived([...tempData, ...Array(predictedTemp.length).fill(null)])
	const extendedGasData = $derived([...gasData, ...Array(predictedGas.length).fill(null)])

	$effect(() => {
		console.log('updated sensor data:', Array.from(sensorData))

		const currentLength = sensorData.length

		if (currentLength > lastLength) {
			// Extract all temps and gases for training
			const allTemps = sensorData.map(d => d.temperature)
			const allGases = sensorData.map(d => d.gas)

			// Process each new entry
			for (let i = lastLength; i < currentLength; i++) {
				// Need at least LOOKBACK + 1 entries to form a training sample
				// Features from indices i-LOOKBACK to i-1, target at i
				if (i >= LOOKBACK) {
					const features = buildFeatures(allTemps, allGases, i - 1)
					if (features) {
						const target = new Float64Array([allTemps[i], allGases[i]])
						solver.update(features, target)
					}
				}
			}

			lastLength = currentLength

			// Solve for weights if we have enough data
			if (currentLength >= LOOKBACK + 1) {
				weights = solver.solve()
				console.log('Solver weights updated')

				// Perform inference
				performInference(allTemps, allGases, weights)
				console.log('Predictions:', { temp: predictedTemp, gas: predictedGas })
			}
		}
	})
</script>

<div class="w-full flex flex-col gap-4">
	<h2 class="text-xl font-semibold">Data Sensor History (Latest 20 Entries)</h2>
	<!-- Tabs -->
	<div class="flex gap-4 mb-4">
		<button
			class="px-4 py-2 rounded-t-lg border-b-2"
			class:border-blue-500={activeTab === 'all'}
			class:border-gray-200={activeTab !== 'all'}
			onclick={() => (activeTab = 'all')}
		>
			All
		</button>
		<button
			class="px-4 py-2 rounded-t-lg border-b-2"
			class:border-blue-500={activeTab === 'temp'}
			class:border-gray-200={activeTab !== 'temp'}
			onclick={() => (activeTab = 'temp')}
		>
			Temperature
		</button>
		<button
			class="px-4 py-2 rounded-t-lg border-b-2"
			class:border-blue-500={activeTab === 'gas'}
			class:border-gray-200={activeTab !== 'gas'}
			onclick={() => (activeTab = 'gas')}
		>
			Gas
		</button>
	</div>
	<div class="w-full mx-auto">
		<LineChart
			series={[
				...(activeTab !== 'gas'
					? [{ data: extendedTempData, label: 'Temperature', color: '#ef4444' }]
					: []),
				...(activeTab !== 'temp'
					? [{ data: extendedGasData, label: 'Gas', color: '#3b82f6' }]
					: []),
				...(activeTab !== 'gas' && predictedTemp.length > 0
					? [
							{
								data: predictedTempSeries,
								label: 'Temp (Predicted)',
								color: '#f97316',
							},
						]
					: []),
				...(activeTab !== 'temp' && predictedGas.length > 0
					? [
							{
								data: predictedGasSeries,
								label: 'Gas (Predicted)',
								color: '#8b5cf6',
							},
						]
					: []),
			]}
			time={extendedTimeData}
		/>
	</div>
</div>
