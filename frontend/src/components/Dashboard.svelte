<script lang="ts">
	import { onMount } from 'svelte'
	import { apiPost, apiGet } from '../utils/api'
	import Chat, { type ChatMessage } from './Chat.svelte'

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
	let wsConnected = $state(false)

	type ToolCall = {
		name: string
		arguments: Record<string, unknown>
		output: string
	}

	type ChatResponse = {
		messages: ChatMessage[]
		tool_calls: ToolCall[]
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

		const websocket = new WebSocket(wsUrl)

		websocket.addEventListener('open', () => {
			console.log('WebSocket connected')
			wsConnected = true
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
			wsConnected = false
		})

		websocket.addEventListener('close', () => {
			console.log('WebSocket disconnected')
			wsConnected = false
		})

		ws = websocket
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

	onMount(() => {
		fetchDashboardData()
		fetchPollStatus()

		// Cleanup WebSocket on unmount
		return () => {
			if (ws) {
				ws.close()
			}
		}
	})

	$effect(() => {
		console.log('updated sensor data:', Array.from(sensorData))
	})
</script>

<div class="flex gap-6 w-full max-h-screen justify-center">
	<!-- Main dashboard content -->
	<div class="w-full max-w-5xl p-4">
		<div class="bg-white h-full p-6">
			<div class="flex items-center justify-between mb-6">
				<div>
					<h1 class="text-3xl font-bold">Dashboard</h1>
					<p class="text-gray-600 mt-2">Welcome, {username}</p>
				</div>
				<button
					onclick={handleLogout}
					disabled={loading}
					class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
				>
					{loading ? 'Logging out...' : 'Logout'}
				</button>
			</div>

			<div class="border-t pt-6">
				<h2 class="text-xl font-semibold mb-4">IoT Dashboard</h2>
				{#if fetchError}
					<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
						{fetchError}
					</div>
				{:else}
					<p class="text-gray-600">Dashboard content will appear here.</p>
				{/if}
			</div>

			<div class="border-t pt-6 mt-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold">Sensor Polling</h2>
					<div class="flex items-center gap-4">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded-full {wsConnected ? 'bg-blue-500' : 'bg-gray-400'}"></div>
							<p class="text-sm text-gray-600">
								{wsConnected ? 'Live' : 'Offline'}
							</p>
						</div>
						<button
							onclick={togglePolling}
							disabled={pollingLoading}
							class="px-4 py-2 rounded-md text-white font-medium disabled:bg-gray-400 disabled:cursor-not-allowed {isPolling
								? 'bg-red-600 hover:bg-red-700'
								: 'bg-green-600 hover:bg-green-700'}"
						>
							{pollingLoading ? 'Loading...' : isPolling ? 'Stop Polling' : 'Start Polling'}
						</button>
					</div>
				</div>
				<div class="flex items-center gap-2 mb-2">
					<div class="w-3 h-3 rounded-full {isPolling ? 'bg-green-500' : 'bg-gray-400'}"></div>
					<p class="text-gray-600">
						Polling: {isPolling ? 'Active' : 'Inactive'}
					</p>
				</div>
				{#if sensorData.length > 0}
					<p class="text-sm text-gray-500 mt-2">
						{sensorData.length} sensor readings (real-time updates enabled, check console for details)
					</p>
				{/if}
			</div>
		</div>
	</div>

	<!-- Chat sidebar -->
	<Chat onSendMessage={handleChatMessage} />
</div>
