<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import { resolve } from '$app/paths';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>headscale-lite · WireGuard overlay dashboard</title>
	<meta
		name="description"
		content="Panel de operaciones del overlay WireGuard: nodos registrados, heartbeats y conectividad probada entre pares."
	/>
</svelte:head>

<div class="flex min-h-dvh flex-col bg-slate-950 text-slate-200 antialiased">
	<header class="sticky top-0 z-20 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
		<div
			class="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"
		>
			<div class="flex items-start gap-3">
				<span
					aria-hidden="true"
					class="mt-0.5 grid size-10 shrink-0 place-items-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.6"
						stroke-linecap="round"
						stroke-linejoin="round"
						class="size-5"
					>
						<circle cx="12" cy="5" r="2.5" />
						<circle cx="5" cy="18" r="2.5" />
						<circle cx="19" cy="18" r="2.5" />
						<path d="M10.8 7.2 6.2 15.8M13.2 7.2l4.6 8.6M7.5 18h9" />
					</svg>
				</span>
				<div class="min-w-0">
					<p class="font-mono text-[0.65rem] tracking-[0.3em] text-emerald-400/80 uppercase">
						headscale-lite
					</p>
					<h1 class="text-lg font-semibold text-slate-50 sm:text-xl">
						WireGuard overlay dashboard
					</h1>
					<p class="max-w-2xl text-xs text-slate-400 sm:text-sm">
						Estado del plano de control: nodos registrados, heartbeats y conectividad probada entre
						pares.
					</p>
				</div>
			</div>

			<nav aria-label="Navegación principal" class="flex shrink-0 items-center">
				<a
					href={resolve('/')}
					aria-current="page"
					class="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm font-medium text-emerald-300 transition-colors hover:border-emerald-400/50 hover:bg-emerald-500/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
				>
					<span aria-hidden="true" class="size-1.5 rounded-full bg-emerald-400"></span>
					Panel de operaciones
				</a>
			</nav>
		</div>
	</header>

	<main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
		{@render children()}
	</main>

	<footer class="border-t border-slate-800/80 bg-slate-950">
		<div
			class="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-4 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"
		>
			<p>
				Stack:
				<span class="text-slate-400">SvelteKit 3 · Svelte 5 · Bun · FastAPI · WireGuard</span>
			</p>
			<p class="font-mono text-[0.7rem] text-slate-600">
				sin claves en el navegador · solo lecturas
			</p>
		</div>
	</footer>
</div>

<style>
	:global(html) {
		color-scheme: dark;
		background-color: #020617;
	}

	:global(body) {
		background-color: #020617;
	}
</style>
