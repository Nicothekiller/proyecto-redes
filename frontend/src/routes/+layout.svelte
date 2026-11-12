<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { resolve } from '$app/paths';
	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();
	let logoutError = $state(false);

	async function logout() {
		logoutError = false;
		try {
			const response = await fetch('/api/logout', {
				method: 'POST',
				headers: { 'content-type': 'application/json' }
			});
			if (response.ok) {
				window.location.assign('/login');
			} else {
				logoutError = true;
			}
		} catch {
			logoutError = true;
		}
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>headscale-lite · Panel de red</title>
	<meta name="description" content="Estado de los nodos y conexiones del overlay WireGuard." />
</svelte:head>

<div class="flex min-h-dvh flex-col bg-white text-slate-800 antialiased">
	<header class="border-b border-slate-200">
		<div
			class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8"
		>
			<a href={resolve('/')} class="flex items-center gap-3 text-slate-900">
				<span
					class="grid size-9 place-items-center rounded-lg bg-blue-600 text-sm font-semibold text-white"
					aria-hidden="true">h</span
				>
				<span class="text-base font-semibold tracking-tight">headscale-lite</span>
			</a>
			{#if data.role}
				<div class="flex items-center gap-4">
					<span class="text-sm text-slate-500"
						>{data.role === 'admin' ? 'Administrador' : 'Solo lectura'}</span
					>
					<button
						type="button"
						onclick={logout}
						class="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-blue-600"
						>Cerrar sesión</button
					>
					{#if logoutError}<span role="alert" class="text-sm text-rose-700"
							>No se pudo cerrar sesión</span
						>{/if}
				</div>
			{/if}
		</div>
	</header>
	<main class="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
		{@render children()}
	</main>
	<footer class="border-t border-slate-200">
		<div class="mx-auto max-w-7xl px-4 py-5 text-xs text-slate-500 sm:px-6 lg:px-8">
			headscale-lite · WireGuard overlay
		</div>
	</footer>
</div>
