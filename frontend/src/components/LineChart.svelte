<script lang="ts">
	type Series = {
		data: (number | null)[]
		label?: string
		color: string
	}

	type Props = {
		series?: Series[]
		time?: string[]
	}

	let { series = [], time = [] }: Props = $props()

	const WIDTH = 700
	const HEIGHT = 300
	const PADDINGX = 50
	const PADDINGY = 20

	// Tooltip state
	let tooltip = $state<{
		x: number
		y: number
		value: number
		color: string
		label?: string
	} | null>(null)
	let chartContainer: HTMLDivElement

	// Compute domain from all series (filter out nulls)
	const allData = $derived.by(() =>
		series.flatMap(s => s.data).filter((v): v is number => v !== null),
	)

	const yDomainMin = $derived(allData.length ? Math.max(0, Math.min(...allData) - 5) : 0)
	const yDomainMax = $derived(allData.length ? Math.max(...allData) + 5 : 35)

	const yScale = $derived.by(() => {
		const range = HEIGHT - 2 * PADDINGY
		const denom = yDomainMax - yDomainMin
		return (value: number) => range * (1 - (value - yDomainMin) / denom) + PADDINGY
	})

	const xScale = $derived.by(() => {
		const maxLen = Math.max(...series.map(s => s.data.length), 0)
		const step = (WIDTH - 2 * PADDINGX) / Math.max(1, maxLen - 1)
		return (index: number) => index * step + PADDINGX
	})

	// Convert array to SVG path, breaking at null values
	function toPath(arr: (number | null)[]): string {
		let path = ''
		let needsMove = true

		for (let i = 0; i < arr.length; i++) {
			const v = arr[i]
			if (v === null) {
				needsMove = true
				continue
			}
			const cmd = needsMove ? 'M' : 'L'
			path += ` ${cmd} ${xScale(i)} ${yScale(v)}`
			needsMove = false
		}

		return path
	}

	// Compute paths and points for each series
	const seriesData = $derived.by(() =>
		series
			.filter(s => s.data.length > 0)
			.map(s => {
				const validPoints: { x: number; y: number; v: number; i: number }[] = []
				for (let i = 0; i < s.data.length; i++) {
					const v = s.data[i]
					if (v !== null) {
						validPoints.push({ x: xScale(i), y: yScale(v), v, i })
					}
				}
				return {
					...s,
					path: toPath(s.data),
					points: validPoints,
				}
			}),
	)

	// Y axis labels
	const yLabels = $derived.by(() => {
		if (!allData.length) return []
		const labels: { val: string; y: number }[] = []
		for (let i = 0; i < 5; i++) {
			const t = yDomainMin + ((yDomainMax - yDomainMin) / 4) * i
			labels.push({ val: t.toFixed(0), y: yScale(t) })
		}
		return labels
	})

	function showTooltip(event: MouseEvent, value: number, color: string, label?: string) {
		const rect = chartContainer.getBoundingClientRect()
		const target = event.currentTarget as SVGCircleElement
		const cx = parseFloat(target.getAttribute('cx') || '0')
		const cy = parseFloat(target.getAttribute('cy') || '0')

		// Convert SVG coordinates to container coordinates
		const scaleX = rect.width / WIDTH
		const scaleY = rect.height / HEIGHT

		tooltip = {
			x: cx * scaleX,
			y: cy * scaleY,
			value,
			color,
			label,
		}
	}

	function hideTooltip() {
		tooltip = null
	}

	// Filter series with labels for legend
	const legendItems = $derived(series.filter(s => s.label && s.data.length > 0))

	// Legend position as percentage of container width
	const legendLeft = (PADDINGX / WIDTH) * 100
</script>

<div class="relative" bind:this={chartContainer}>
	<!-- Legend -->
	{#if legendItems.length > 0}
		<div
			class="absolute top-4 flex flex-col gap-1 bg-white/90 rounded-lg px-3 py-2 shadow-sm border border-gray-100"
			style="left: calc({legendLeft}% + 0.5rem)"
		>
			{#each legendItems as item}
				<div class="flex items-center gap-2 text-xs">
					<span class="w-3 h-3 rounded-full" style="background-color: {item.color}"></span>
					<span class="text-gray-600 font-medium">{item.label}</span>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Tooltip -->
	{#if tooltip}
		<div
			class="absolute pointer-events-none z-10 px-2 py-1 rounded text-xs text-white font-medium shadow-lg"
			style="
				left: {tooltip.x}px;
				top: {tooltip.y}px;
				transform: translate(-50%, -100%) translateY(-8px);
				background-color: {tooltip.color};
			"
		>
			{#if tooltip.label}
				<span class="opacity-75">{tooltip.label}:</span>
			{/if}
			{tooltip.value}
		</div>
	{/if}

	<svg width="100%" height="auto" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
		<!-- Grid Y -->
		{#each yLabels as label}
			<line
				x1={PADDINGX}
				y1={label.y}
				x2={WIDTH - PADDINGX}
				y2={label.y}
				stroke="#eee"
				stroke-dasharray="4 4"
			/>
			<text x={PADDINGX - 6} y={label.y + 4} text-anchor="end" font-size="12" fill="#555">
				{label.val}
			</text>
		{/each}

		<!-- Time labels -->
		{#each time as t, index}
			<text
				x={xScale(index)}
				y={HEIGHT - PADDINGY + 20}
				text-anchor="middle"
				font-size="12"
				opacity={index % 3 == 0 ? 1 : 0}
				fill="#555"
			>
				{t}
			</text>
		{/each}

		<!-- Axis -->
		<line
			x1={PADDINGX}
			y1={HEIGHT - PADDINGY}
			x2={WIDTH - PADDINGX}
			y2={HEIGHT - PADDINGY}
			stroke="#333"
		/>
		<line x1={PADDINGX} y1={PADDINGY} x2={PADDINGX} y2={HEIGHT - PADDINGY} stroke="#333" />

		<!-- Chart lines and points -->
		<g class="slide-container">
			{#each seriesData as s}
				<!-- Line -->
				<path d={s.path} stroke={s.color} stroke-width="2" fill="none" stroke-linecap="round" />

				<!-- Points -->
				{#each s.points as p}
					<g class="cursor-pointer">
						<!-- Visible circle -->
						<circle cx={p.x} cy={p.y} r="4" fill={s.color} stroke="white" stroke-width="2" />
						<!-- Invisible larger hit area -->
						<circle
							cx={p.x}
							cy={p.y}
							r="12"
							fill="transparent"
							onmouseenter={e => showTooltip(e, p.v, s.color, s.label)}
							onmouseleave={hideTooltip}
							role="img"
						/>
					</g>
				{/each}
			{/each}
		</g>
	</svg>
</div>

<style>
	.slide-container {
		transition: transform 0.45s cubic-bezier(0.45, 0, 0.25, 1);
	}
</style>
