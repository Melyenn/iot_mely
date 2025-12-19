<script lang="ts">
	let { data1 = [], data2 = [], time = [] } = $props()

	const WIDTH = 700
	const HEIGHT = 300
	const PADDINGX = 50
	const PADDINGY = 20

	/* ------------------------------------
        Tính domain cho cả 2 series
    ------------------------------------ */
	const allData = $derived.by(() => [...data1, ...data2].filter(Number.isFinite))

	const yDomainMin = $derived(allData.length ? Math.max(0, Math.min(...allData) - 5) : 0)
	const yDomainMax = $derived(allData.length ? Math.max(...allData) + 5 : 35)

	const yScale = $derived.by(() => {
		const range = HEIGHT - 2 * PADDINGY
		const denom = yDomainMax - yDomainMin
		return value => range * (1 - (value - yDomainMin) / denom) + PADDINGY
	})

	const xScale = $derived.by(() => {
		const maxLen = Math.max(data1.length, data2.length)
		const step = (WIDTH - 2 * PADDINGX) / Math.max(1, maxLen - 1)
		return index => index * step + PADDINGX
	})

	/* ------------------------------------
        Convert mảng -> path SVG
    ------------------------------------ */
	function toPath(arr) {
		return arr.map((v, i) => ` ${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(v)}`).join('')
	}

	const path1 = $derived.by(() => toPath(data1))
	const path2 = $derived.by(() => toPath(data2))

	const points1 = $derived.by(() => data1.map((v, i) => ({ x: xScale(i), y: yScale(v), v })))
	const points2 = $derived.by(() => data2.map((v, i) => ({ x: xScale(i), y: yScale(v), v })))

	/* Y labels */
	const yLabels = $derived.by(() => {
		if (!allData.length) return []
		const labels = []
		for (let i = 0; i < 5; i++) {
			const t = yDomainMin + ((yDomainMax - yDomainMin) / 4) * i
			labels.push({ val: t.toFixed(0), y: yScale(t) })
		}
		return labels
	})
</script>

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
		<text x={PADDINGX - 6} y={label.y + 4} text-anchor="end" font-size="12" fill="#555"
			>{label.val}</text
		>
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

	<!-- CHART GROUP -->
	<g class="slide-container">
		<!-- LINE 1 -->
		<path d={path1} stroke="red" stroke-width="2" fill="none" stroke-linecap="round" />
		{#each points1 as p}
			<circle cx={p.x} cy={p.y} r="3" fill="red" />
		{/each}

		{#each points1 as p}
			<g class="group pointer-events-auto">
				<circle cx={p.x} cy={p.y} r="3" fill="red" stroke="white" stroke-width="1" />

				<!-- Tooltip -->
				<rect
					x={p.x - 20}
					y={p.y - 30}
					width="40"
					height="20"
					rx="4"
					ry="4"
					fill="#333"
					opacity="0.9"
					class="hidden group-hover:block"
				/>

				<text
					x={p.x}
					y={p.y - 15}
					text-anchor="middle"
					font-size="12"
					fill="white"
					class="hidden group-hover:block"
				>
					{p.v}
				</text>
			</g>
		{/each}

		<!-- LINE 2 -->
		<path d={path2} stroke="blue" stroke-width="2" fill="none" stroke-linecap="round" />
		{#each points2 as p}
			<circle cx={p.x} cy={p.y} r="3" fill="blue" />
		{/each}

		{#each points2 as p}
			<g class="group pointer-events-auto">
				<circle cx={p.x} cy={p.y} r="3" fill="blue" stroke="white" stroke-width="1" />

				<!-- Tooltip -->
				<rect
					x={p.x - 20}
					y={p.y - 30}
					width="40"
					height="20"
					rx="4"
					ry="4"
					fill="#333"
					opacity="0.9"
					class="hidden group-hover:block"
				/>

				<text
					x={p.x}
					y={p.y - 15}
					text-anchor="middle"
					font-size="12"
					fill="white"
					class="hidden group-hover:block"
				>
					{p.v}
				</text>
			</g>
		{/each}
	</g>
</svg>

<style>
	.slide-container {
		transition: transform 0.45s cubic-bezier(0.45, 0, 0.25, 1);
	}
</style>
