<script lang="ts">
	import { tick } from 'svelte'
	import MessageBody from './MessageBody.svelte'

	export type ChatMessage = {
		role: 'user' | 'assistant'
		content: string
	}

	type Props = {
		onSendMessage: (history: ChatMessage[]) => Promise<ChatMessage[]>
		open: boolean
		onClose?: () => void
	}

	let { onSendMessage, open, onClose }: Props = $props()

	let messages = $state<ChatMessage[]>([])
	let inputText = $state('')
	let isLoading = $state(false)
	let chatContainer: HTMLDivElement

	async function scrollToBottom() {
		await tick()
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight
		}
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault()
		const text = inputText.trim()
		if (!text || isLoading) return

		messages.push({ role: 'user', content: text })
		inputText = ''
		await scrollToBottom()

		isLoading = true
		try {
			const newMessages = await onSendMessage(messages)
			for (const msg of newMessages) {
				messages.push(msg)
			}
			await scrollToBottom()
		} catch (err) {
			console.error('Chat error:', err)
			messages.push({
				role: 'assistant',
				content: 'Sorry, something went wrong. Please try again.',
			})
			await scrollToBottom()
		} finally {
			isLoading = false
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault()
			const form = (e.target as HTMLElement).closest('form')
			form?.requestSubmit()
		}
	}
</script>

{#if open}
	<div class="p-4 w-lg shrink-0 flex flex-col">
		<div class="flex justify-between items-center px-4 py-3 border-b border-slate-200 bg-white">
			<h2 class="text-lg font-semibold text-slate-800">AI Assistant</h2>
			<button
				onclick={onClose}
				class="text-slate-500 hover:text-slate-800 transition-colors"
				aria-label="Close chat"
			>
				✕
			</button>
		</div>

		<div bind:this={chatContainer} class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
			{#each messages as message}
				<div
					class="{message.role === 'user'
						? 'max-w-[90%] ml-auto bg-white border-2 border-slate-200 text-slate-800'
						: 'bg-slate-700 text-slate-100'} rounded-xl p-4"
				>
					<MessageBody content={message.content} variant={message.role} />
				</div>
			{/each}
			{#if isLoading}
				<div class="mr-auto bg-slate-700 text-slate-100 rounded-xl p-4 text-sm">
					<span class="inline-flex gap-1">
						<span class="animate-bounce">●</span>
						<span class="animate-bounce" style="animation-delay: 0.1s">●</span>
						<span class="animate-bounce" style="animation-delay: 0.2s">●</span>
					</span>
				</div>
			{/if}
			{#if messages.length === 0 && !isLoading}
				<p class="text-center text-slate-400 text-sm mt-8">Start a conversation...</p>
			{/if}
		</div>

		<form onsubmit={handleSubmit} class="p-3 border-t border-slate-200 bg-white">
			<div class="flex gap-2">
				<textarea
					bind:value={inputText}
					onkeydown={handleKeydown}
					placeholder="Type a message..."
					rows="2"
					disabled={isLoading}
					class="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed"
				></textarea>
				<button
					type="submit"
					disabled={isLoading || !inputText.trim()}
					class="self-end px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-slate-400 disabled:cursor-not-allowed transition-colors"
				>
					Send
				</button>
			</div>
		</form>
	</div>
{/if}
