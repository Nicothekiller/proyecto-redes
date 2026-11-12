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

<div class="flex min-h-dvh flex-col bg-[#f7f9fc] text-slate-800 antialiased">
	<header class="border-b border-slate-200/80 bg-white">
		<div
			class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8"
		>
			<a href={resolve('/')} class="flex items-center gap-3 text-slate-900">
				<span
					class="grid size-10 place-items-center rounded-xl bg-blue-700 text-white shadow-sm shadow-blue-900/20"
					aria-hidden="true"
				>
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.6"
						class="size-6"
					>
						<circle cx="12" cy="5" r="2.25" /><circle cx="5" cy="18" r="2.25" /><circle
							cx="19"
							cy="18"
							r="2.25"
						/>
						<path d="M10.8 7 6.2 16M13.2 7l4.6 9M7.5 18h9" />
					</svg>
				</span>
				<span class="flex flex-col"
					><span class="text-base font-semibold tracking-tight">headscale-lite</span><span
						class="text-xs text-slate-500">WireGuard overlay</span
					></span
				>
			</a>
			{#if data.role}
				<div class="flex items-center gap-4">
					<span
						class="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600"
						>{data.role === 'admin' ? 'Administrador' : 'Solo lectura'}</span
					>
					<button
						type="button"
						onclick={logout}
						class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm transition-colors hover:border-slate-300 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-blue-600"
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
	<footer class="border-t border-slate-200/80 bg-white">
		<div class="mx-auto max-w-7xl px-4 py-5 text-xs text-slate-500 sm:px-6 lg:px-8">
			headscale-lite · WireGuard overlay
		</div>
	</footer>
</div>
