<script lang="ts">
	import { onMount } from 'svelte'
	import { apiPost, apiGet } from '../utils/api'
	import SensorHistory from './SensorHistory.svelte'
	import PopupButton from './PopupButton.svelte'
	import Chat, { type ChatMessage } from './Chat.svelte'
	import chatIcon from './icons/chat.svg?raw'

	type Props = {
		username: string
		onLogout: () => void
	}

	type SensorData = {
		id: number
		timestamp: Date
		temperature: number
		gas: number
	}

	type SensorDataRaw = {
		id: number
		timestamp: string
		temperature: number
		gas: number
	}

	type DashboardResponse = {
		username: string
		sensor_data?: SensorDataRaw[]
	}

	type PollStatus = {
		is_polling: boolean
	}

	let { username, onLogout }: Props = $props()

	let loading = $state(false)
	let sensorData = $state<SensorData[]>([])
	let fetchError = $state<string | null>(null)
	let isPolling = $state(false)
	let pollingLoading = $state(false)
	let ws: WebSocket | null = $state(null)

	let temp = $derived(sensorData.at(-1)?.temperature ?? 20)
	const maxTemp = 200
	let gas = $derived(sensorData.at(-1)?.gas ?? 0)
	const maxGas = 8000

	let onBuzzer: boolean = $state(false)
	let onRelay: boolean = $state(false)

	type StateLed = '#d43008' | '#22c55e' | '#eab308'

	let led_last = $state<StateLed | null>(null)

	function getLedState(temp: number, gas: number): StateLed {
		console.log(temp, ' - ', gas)
		if (temp >= 70) return '#d43008'
		if (temp >= 50 || gas >= 3000) return '#eab308'
		return '#22c55e'
	}

	let led: StateLed = $state('#22c55e')
	type ToolCall = {
		name: string
		arguments: Record<string, unknown>
		output: string
	}

	type ChatResponse = {
		messages: ChatMessage[]
		tool_calls: ToolCall[]
	}

	// Process tool calls and update UI state accordingly
	function processToolCalls(toolCalls: ToolCall[]) {
		for (const toolCall of toolCalls) {
			switch (toolCall.name) {
				case 'set_sensor_polling':
					{
						const enabled = !!toolCall.arguments.enabled
						isPolling = enabled
					}
					break
				case 'set_relay':
					{
						const enabled = !!toolCall.arguments.enabled
						onRelay = enabled
					}
					break
				case 'set_buzzer':
					{
						const enabled = !!toolCall.arguments.enabled
						onBuzzer = enabled
					}
					break
			}
		}
	}

	// Chat callback - calls the backend API
	async function handleChatMessage(history: ChatMessage[]): Promise<ChatMessage[]> {
		const response = await apiPost<ChatResponse>(
			'/chat/',
			{ messages: history },
			{ handleLogout: onLogout },
		)

		// Log tool calls to console
		if (response.tool_calls.length > 0) {
			console.group('Tool Calls')
			for (const toolCall of response.tool_calls) {
				console.log(`${toolCall.name}(`, toolCall.arguments, ')')
				console.log('Output:', toolCall.output)
			}
			console.groupEnd()

			// Update UI state based on tool calls
			processToolCalls(response.tool_calls)
		}

		return response.messages
	}

	function connectWebSocket() {
		// Close existing connection if any
		if (ws) {
			ws.close()
		}

		// Determine WebSocket URL
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
		const wsUrl = `${protocol}//${window.location.host}/ws`
		console.log(wsUrl)

		const websocket = new WebSocket(wsUrl)

		websocket.addEventListener('open', () => {
			console.log('WebSocket connected')
			ws = websocket
		})

		websocket.addEventListener('message', event => {
			try {
				const rawData: SensorDataRaw = JSON.parse(event.data)
				// Add new data to the beginning of the array
				sensorData.push({
					...rawData,
					timestamp: new Date(rawData.timestamp),
				})
			} catch (err) {
				console.error('Failed to parse WebSocket message:', err)
			}
		})

		websocket.addEventListener('error', error => {
			console.error('WebSocket error:', error)
			ws = null
		})

		websocket.addEventListener('close', () => {
			console.log('WebSocket disconnected')
			ws = null
		})
	}

	async function fetchDashboardData() {
		try {
			const response = await apiGet<DashboardResponse>('/dashboard/', {
				handleLogout: onLogout,
			})

			// Parse timestamps to Date objects
			if (response.sensor_data) {
				for (const dataPoint of response.sensor_data) {
					sensorData.push({
						...dataPoint,
						timestamp: new Date(dataPoint.timestamp),
					})
				}
			}
			fetchError = null

			// Log sensor data to console
			if (sensorData.length > 0) {
				console.log('Sensor data from last 3 days:', sensorData)
			}

			// Connect WebSocket (uses cookie authentication)
			connectWebSocket()
		} catch (err) {
			console.error('Failed to fetch dashboard data:', err)
			fetchError = err instanceof Error ? err.message : 'Failed to load dashboard data'
		}
	}

	async function fetchPollStatus() {
		try {
			const data = await apiGet<PollStatus>('/dashboard/poll/status', {
				handleLogout: onLogout,
			})
			isPolling = data.is_polling
		} catch (err) {
			console.error('Failed to fetch poll status:', err)
		}
	}

	async function togglePolling() {
		pollingLoading = true
		try {
			const data = await apiPost<PollStatus>('/dashboard/poll/toggle', undefined, {
				handleLogout: onLogout,
			})
			isPolling = data.is_polling
			console.log(data.is_polling ? 'Polling started' : 'Polling stopped')
		} catch (err) {
			console.error('Failed to toggle polling:', err)
		} finally {
			pollingLoading = false
		}
	}

	async function handleLogout() {
		loading = true
		try {
			await apiPost('/auth/logout')
			onLogout()
		} catch (err) {
			console.error('Logout failed:', err)
			// Still call onLogout to clear the UI state
			onLogout()
		} finally {
			loading = false
		}
	}

	async function handleRelay() {
		onRelay = !onRelay
		try {
			await apiPost('/dashboard/devices/relay', { onRelay: onRelay })
		} catch (err) {
			console.error('Relay failed:', err)
		}
	}

	async function handleBuzzer() {
		onBuzzer = !onBuzzer
		try {
			await apiPost('/dashboard/devices/buzzer', { onBuzzer: onBuzzer })
		} catch (err) {
			console.error('Buzzer failed:', err)
		}
	}

	async function handleLed(ledColor: string) {
		try {
			await apiPost('/dashboard/devices/led', { ledColor: ledColor })
		} catch (err) {
			console.error('Led failed:', err)
		}
	}

	onMount(() => {
		fetchDashboardData()
		fetchPollStatus()

		// Cleanup WebSocket on unmount
		return () => {
			console.log('disconnected WS')
			if (ws) {
				ws.close()
			}
		}
	})

	$effect(() => {
		led = getLedState(sensorData.at(-1)?.temperature || 0, sensorData.at(-1)?.gas || 0)
		if (led_last === null || led_last !== led) {
			console.log('12')
			led_last = led
			if (led === '#d43008') {
				handleLed('red')
				onBuzzer = false
				onRelay = false
				handleBuzzer()
				handleRelay()
			} else if (led === '#eab308') {
				handleLed('yellow')
			} else {
				handleLed('green')
			}
		}
		console.log(led)
	})

	function getTempColor(t: number) {
		if (t >= 70) return '#d43008'
		if (t >= 50) return '#eab308'
		return '#22c55e' // xanh lá
	}

	function getGasColor(t: number) {
		if (t >= 3000) return '#eab308'
		return '#22c55e'
	}

	function handleReset() {
		led = '#22c55e'
		onBuzzer = true
		onRelay = true
		handleBuzzer()
		handleRelay()
	}
</script>

<div class="flex w-full max-h-screen justify-center">
	<!-- Main dashboard content -->
	<div class="w-full max-w-6xl p-4">
		<div class="bg-white h-full p-6 overflow-y-auto">
			<div class="flex items-center justify-between mb-6">
				<header class="flex items-center justify-between w-full">
					<div class="flex items-center gap-4">
						<div class="bg-[#FF4D00] rounded-2xl p-2.5 shadow-lg shadow-orange-100/50">
							<svg class="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 24 24">
								<path
									d="M12 2C12 2 12 5.79 12 7.19C12 8.59 12.79 10 14.19 10C15.59 10 17 8.59 17 7.19C17 5.79 17 2 17 2C17 2 21 6 21 11C21 16 17 20 12 20C7 20 3 16 3 11C3 6 7 2 12 2Z"
								/>
							</svg>
						</div>
						<div>
							<h1 class="text-2xl font-extrabold tracking-tight text-gray-900">FireGuard</h1>
						</div>
					</div>

					<div class="flex items-center gap-6">
						<div
							class="flex items-center gap-2 rounded-full border px-4 py-1.5 {led === '#22c55e'
								? 'border-green-100 bg-green-50 text-green-700'
								: led === '#eab308'
									? 'border-yellow-100 bg-yellow-50 text-yellow-700'
									: 'border-red-100 bg-red-50 text-red-700'}"
						>
							<span
								class="h-2.5 w-2.5 rounded-full animate-pulse {led === '#22c55e'
									? 'bg-green-500'
									: led === '#eab308'
										? 'bg-yellow-500'
										: 'bg-red-500'}"
							></span>
							<span class="text-sm font-bold">
								{led === '#22c55e' ? 'Stable' : led === '#eab308' ? 'Warning' : 'Serious'}
							</span>
						</div>

						<div class="flex items-center gap-4 text-gray-500">
							<span class="text-sm font-bold">Welcome, {username}</span>
							<button
								onclick={handleLogout}
								disabled={loading}
								class="text-gray-400 transition-colors hover:text-red-500 disabled:opacity-50"
								aria-label="Logout"
							>
								<svg
									class="h-5 w-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
									xmlns="http://www.w3.org/2000/svg"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
									/>
								</svg>
							</button>
						</div>
					</div>
				</header>
			</div>
			{#if fetchError}
				<div>
					<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
						{fetchError}
					</div>
				</div>
			{:else}
				<div>
					<div class="border-t border-slate-300 py-6 flex flex-row gap-2">
						<div
							class="flex items-center gap-2 rounded-lg border border-gray-100 bg-white px-3 py-1.5 text-[11px] font-bold text-gray-500 shadow-sm"
						>
							<div class="w-3 h-3 rounded-full {isPolling ? 'bg-green-500' : 'bg-gray-400'}"></div>
							<p class="text-gray-600">
								Polling: {isPolling ? 'Active' : 'Inactive'}
							</p>
						</div>
						<div
							class="flex items-center gap-2 rounded-lg border border-gray-100 bg-white px-3 py-1.5 text-[11px] font-bold text-gray-500 shadow-sm"
						>
							<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							Update: {sensorData.at(-1)?.timestamp.toLocaleTimeString('vi-VN') ??
								new Date().toLocaleTimeString('vi-VN')}
						</div>
						<div
							class="flex items-center gap-2 rounded-lg border border-gray-100 bg-white px-3 py-1.5 text-[11px] font-bold text-gray-500 shadow-sm"
						>
							<span class="w-2 h-2 rounded-full {ws ? 'bg-blue-500' : 'bg-gray-400'}"></span>
							{ws ? 'Live' : 'Offline'}
						</div>
					</div>

					<!-- Main Content -->
					<div class="flex flex-col gap-14">
						<div class="flex flex-row flex-wrap gap-4 justify-between">
							<div
								class="flex flex-col gap-4 p-4 border border-slate-300 rounded-2xl w-fit justify-between"
							>
								<h2 class="flex flex-row gap-3 items-center text-xl font-semibold">Temperature</h2>
								<div class="flex justify-center items-start w-full overflow-hidden">
									<svg
										viewBox="0 0 250 150"
										preserveAspectRatio="xMidYMid meet"
										width="100%"
										height="auto"
									>
										<path
											d="M25,125 A100,100 0 0,1 225,125"
											stroke={getTempColor(temp)}
											stroke-width={30}
											fill="none"
											stroke-linecap="round"
											stroke-opacity={0.1}
										/>
										<path
											d="M25,125 A100,100 0 0,1 225,125"
											stroke={getTempColor(temp)}
											stroke-width={30}
											fill="none"
											stroke-linecap="round"
											stroke-dasharray={314}
											stroke-dashoffset={314 * (1 - Math.min(temp / maxTemp, 1))}
										/>
										<text x="125" y="125" text-anchor="middle" font-size="25" fill="black">
											{temp}°C
										</text>
									</svg>
								</div>
							</div>

							<div
								class="flex flex-col gap-4 p-4 border border-slate-300 rounded-2xl w-fit justify-between"
							>
								<h2 class="flex flex-row gap-3 items-center text-xl font-semibold">Gas</h2>
								<div class="flex justify-center items-start w-full overflow-hidden">
									<svg
										viewBox="0 0 250 150"
										preserveAspectRatio="xMidYMid meet"
										width="100%"
										height="auto"
									>
										<path
											d="M25,125 A100,100 0 0,1 225,125"
											stroke={getGasColor(gas)}
											stroke-width={30}
											fill="none"
											stroke-linecap="round"
											stroke-opacity={0.1}
										/>
										<path
											d="M25,125 A100,100 0 0,1 225,125"
											stroke={getGasColor(gas)}
											stroke-width="30"
											fill="none"
											stroke-linecap="round"
											stroke-dasharray={314}
											stroke-dashoffset={314 * (1 - Math.min(gas / maxGas, 1))}
										/>
										<text x="125" y="125" text-anchor="middle" font-size="25" fill="black">
											{gas}ppm
										</text>
									</svg>
								</div>
							</div>

							<div
								class="border border-slate-300 rounded-2xl p-4 space-y-4 bg-white shadow-sm flex-1"
							>
								<!-- Header -->
								<div class="flex flex-row justify-between items-center gap-5">
									<div class="flex flex-row gap-2 items-center text-xl font-semibold">
										Control Devices
									</div>

									<button
										class="px-4 py-1.5 text-sm font-medium border border-slate-300 rounded-xl
											hover:bg-gray-100 active:scale-95 transition-all"
										onclick={() => handleReset()}
									>
										Reset
									</button>
								</div>

								<!-- List -->
								<ul class="flex flex-col gap-2">
									<li
										class="border border-slate-300 rounded-xl px-4 py-3 flex flex-row justify-between items-center
											bg-gray-50 hover:bg-gray-100 transition-colors"
									>
										<div class="flex flex-row gap-2 items-center">
											<span class="font-medium">Sensor</span>
										</div>

										<div class="flex flex-row gap-2">
											<button
												type="button"
												title="sensor"
												class="relative w-12 h-6 flex items-center bg-gray-300 rounded-full cursor-pointer transition-colors duration-200"
												class:bg-green-500={isPolling}
												onclick={() => togglePolling()}
											>
												<div
													class="absolute bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-200"
													class:translate-x-6={isPolling}
												></div>
											</button>
										</div>
									</li>

									<li
										class="border border-slate-300 rounded-xl px-4 py-3 flex flex-row items-center gap-3
											bg-gray-50 hover:bg-gray-100 transition-colors"
									>
										<svg
											class="bulb-svg"
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 384 512"
											width={25}
											height={25}
											aria-hidden="false"
											role="img"
											aria-label="Bulb icon"
										>
											<path
												class="bulb-path"
												d="M296.5 291.1C321 265.2 336 230.4 336 192 336 112.5 271.5 48 192 48S48 112.5 48 192c0 38.4 15 73.2 39.5 99.1 21.3 22.4 44.9 54 53.3 92.9l102.4 0c8.4-39 32-70.5 53.3-92.9zm34.8 33C307.7 349 288 379.4 288 413.7l0 18.3c0 44.2-35.8 80-80 80l-32 0c-44.2 0-80-35.8-80-80l0-18.3C96 379.4 76.3 349 52.7 324.1 20 289.7 0 243.2 0 192 0 86 86 0 192 0S384 86 384 192c0 51.2-20 97.7-52.7 132.1zM144 184c0 13.3-10.7 24-24 24s-24-10.7-24-24c0-48.6 39.4-88 88-88 13.3 0 24 10.7 24 24s-10.7 24-24 24c-22.1 0-40 17.9-40 40z"
												style="fill: {led};"
											/>
										</svg>
										<span class="font-medium">LED</span>
									</li>

									<li
										class="border border-slate-300 rounded-xl px-4 py-3 flex flex-row justify-between items-center
											bg-gray-50 hover:bg-gray-100 transition-colors"
									>
										<div class="flex flex-row gap-2 items-center">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 448 512"
												width={25}
												height={25}
												class="bell-svg"
											>
												<path
													d="M224 0c-13.3 0-24 10.7-24 24l0 9.7C118.6 45.3 56 115.4 56 200l0 14.5c0 37.7-10 74.7-29 107.3L5.1 359.2C1.8 365 0 371.5 0 378.2 0 399.1 16.9 416 37.8 416l372.4 0c20.9 0 37.8-16.9 37.8-37.8 0-6.7-1.8-13.3-5.1-19L421 321.7c-19-32.6-29-69.6-29-107.3l0-14.5c0-84.6-62.6-154.7-144-166.3l0-9.7c0-13.3-10.7-24-24-24zM392.4 368l-336.9 0 12.9-22.1C91.7 306 104 260.6 104 214.5l0-14.5c0-66.3 53.7-120 120-120s120 53.7 120 120l0 14.5c0 46.2 12.3 91.5 35.5 131.4L392.4 368zM156.1 464c9.9 28 36.6 48 67.9 48s58-20 67.9-48l-135.8 0z"
													fill={onBuzzer ? '#d43008' : '#22c55e'}
												/>
											</svg>
											<span class="font-medium">Buzzer</span>
										</div>

										<button
											type="button"
											title="buzzer"
											class="relative w-12 h-6 flex items-center bg-gray-300 rounded-full cursor-pointer transition-colors duration-200"
											class:bg-red-500={onBuzzer}
											onclick={() => handleBuzzer()}
										>
											<div
												class="absolute bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-200"
												class:translate-x-6={onBuzzer}
											></div>
										</button>
									</li>

									<li
										class="border border-slate-300 rounded-xl px-4 py-3 flex flex-row justify-between items-center
											bg-gray-50 hover:bg-gray-100 transition-colors"
									>
										<div class="flex flex-row gap-2 items-center">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												width={25}
												height={25}
												fill="none"
												stroke={onRelay ? '#d43008' : '#22c55e'}
												stroke-width="2.2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<path
													d="
													M12 2
													Q9 6 7.5 8.8
													Q6 11.5 6 14
													Q6 18 9 20
													Q12 22 15 20
													Q18 18 18 14
													Q18 11.5 16.5 8.8
													Q15 6 12 2
													Z
												"
												/>
											</svg>

											<span class="font-medium">Relay</span>
										</div>

										<button
											type="button"
											title="relay"
											class="relative w-12 h-6 flex items-center bg-gray-300 rounded-full cursor-pointer transition-colors duration-200"
											class:bg-red-500={onRelay}
											onclick={() => handleRelay()}
										>
											<div
												class="absolute bg-white w-5 h-5 rounded-full shadow-md transform transition-transform duration-200"
												class:translate-x-6={onRelay}
											></div>
										</button>
									</li>
								</ul>
							</div>
						</div>

						<SensorHistory {sensorData} />
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Chat sidebar -->
	<PopupButton
		icon={chatIcon}
		buttonClass="bg-indigo-600 text-white hover:bg-indigo-700"
		ariaLabel="Open chat"
	>
		{#snippet children({ close })}
			<Chat onSendMessage={handleChatMessage} onClose={close} />
		{/snippet}
	</PopupButton>
</div>
