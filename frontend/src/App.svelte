<script lang="ts">
	import { onMount } from 'svelte'
	import LoginForm from './components/LoginForm.svelte'
	import RegisterForm from './components/RegisterForm.svelte'
	import Dashboard from './components/Dashboard.svelte'

	type ViewState = 'loading' | 'login' | 'register' | 'dashboard'

	let currentView = $state<ViewState>('loading')
	let username = $state('')

	async function checkAuthentication() {
		try {
			const response = await fetch('/dashboard/')

			if (response.ok) {
				const data: { username: string } = await response.json()
				username = data.username
				currentView = 'dashboard'
			} else {
				currentView = 'login'
			}
		} catch (err) {
			console.error('Authentication check failed:', err)
		}
	}

	function handleLoginSuccess() {
		checkAuthentication()
	}

	function handleRegisterSuccess() {
		checkAuthentication()
	}

	function handleLogout() {
		username = ''
		currentView = 'login'
	}

	function switchToRegister() {
		currentView = 'register'
	}

	function switchToLogin() {
		currentView = 'login'
	}

	onMount(() => {
		checkAuthentication()
	})
</script>

<main class="min-h-screen bg-gray-100 flex items-center justify-center">
	{#if currentView === 'loading'}
		<div class="text-center">
			<div
				class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"
			></div>
			<p class="mt-4 text-gray-600">Loading...</p>
		</div>
	{:else if currentView === 'login'}
		<LoginForm onLoginSuccess={handleLoginSuccess} onSwitchToRegister={switchToRegister} />
	{:else if currentView === 'register'}
		<RegisterForm onRegisterSuccess={handleRegisterSuccess} onSwitchToLogin={switchToLogin} />
	{:else if currentView === 'dashboard'}
		<Dashboard {username} onLogout={handleLogout} />
	{/if}
</main>
