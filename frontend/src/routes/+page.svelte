<script lang="ts">
	import { untrack } from 'svelte';
	import type { Dashboard } from '#lib/types.ts';
	import NodeTable from '#lib/components/NodeTable.svelte';
	import PairTable from '#lib/components/PairTable.svelte';
	import StatusBar from '#lib/components/StatusBar.svelte';
	import type { PageData } from './$types';

	const REFRESH_MS = 5000;

	let { data }: { data: PageData } = $props();

	let dashboardOverride = $state<Dashboard | null>(null);
	let previousDashboard = $state<Dashboard | null>(null);
	let errorOverride = $state<string | null | undefined>(undefined);
	let lastSuccessOverride = $state<string | null>(null);
	let refreshing = $state(false);
	let busy = $state(false);

	let inFlight: AbortController | null = null;

	const dashboard = $derived(dashboardOverride ?? data.dashboard);
	const error = $derived(errorOverride !== undefined ? errorOverride : data.error);
	const lastSuccess = $derived(lastSuccessOverride ?? data.dashboard?.fetchedAt ?? null);
	const previousPairs = $derived(previousDashboard?.status.pairs ?? []);
	const offlineAfterS = $derived(dashboard?.status.offline_after_s ?? 90);
	const asOfMs = $derived.by(() => {
		const raw = dashboard?.status.as_of;
		if (!raw) return Date.now();
		const parsed = Date.parse(raw);
		return Number.isNaN(parsed) ? Date.now() : parsed;
	});

	function isDashboard(value: unknown): value is Dashboard {
		if (!value || typeof value !== 'object') return false;
		const candidate = value as Record<string, unknown>;
		return (
			Array.isArray(candidate.nodes) &&
			typeof candidate.fetchedAt === 'string' &&
			typeof candidate.status === 'object' &&
			candidate.status !== null
		);
	}

	function errorMessage(payload: unknown, status: number): string {
		if (payload && typeof payload === 'object' && 'error' in payload) {
			const message = (payload as { error?: unknown }).error;
			if (typeof message === 'string' && message.length > 0) return message;
		}
		return `el backend respondió con estado ${status}`;
	}

	async function refresh(manual = false): Promise<void> {
		if (inFlight) return;

		const controller = new AbortController();
		inFlight = controller;
		busy = true;
		if (manual) refreshing = true;

		try {
			const response = await fetch('/api/dashboard', {
				signal: controller.signal,
				cache: 'no-store',
				headers: { accept: 'application/json' }
			});
			const payload: unknown = await response.json().catch(() => null);

			if (controller.signal.aborted) return;

			if (!response.ok) {
				errorOverride = errorMessage(payload, response.status);
				return;
			}

			if (!isDashboard(payload)) {
				errorOverride = 'respuesta inválida del backend';
				return;
			}

			previousDashboard = dashboard;
			dashboardOverride = payload;
			lastSuccessOverride = payload.fetchedAt;
			errorOverride = null;
		} catch (cause) {
			if (controller.signal.aborted) return;
			errorOverride = cause instanceof Error ? cause.message : 'no se pudo consultar el dashboard';
		} finally {
			if (inFlight === controller) {
				inFlight = null;
				busy = false;
				refreshing = false;
			}
		}
	}

	$effect(() => {
		let timer: ReturnType<typeof setInterval> | null = null;

		function startTimer() {
			if (timer !== null) return;
			timer = setInterval(() => {
				if (!document.hidden) void refresh();
			}, REFRESH_MS);
		}

		function stopTimer() {
			if (timer === null) return;
			clearInterval(timer);
			timer = null;
		}

		function handleVisibilityChange() {
			if (document.hidden) {
				stopTimer();
				return;
			}
			void refresh();
			startTimer();
		}

		if (!document.hidden) startTimer();
		document.addEventListener('visibilitychange', handleVisibilityChange);

		if (!untrack(() => dashboard)) void refresh();

		return () => {
			stopTimer();
			document.removeEventListener('visibilitychange', handleVisibilityChange);
			inFlight?.abort();
		};
	});
</script>

<div class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
		<div>
			<p class="font-mono text-[0.65rem] tracking-[0.25em] text-emerald-400/80 uppercase">
				plano de control
			</p>
			<h2 class="mt-1 text-2xl font-semibold text-slate-50">Estado del overlay</h2>
			<p class="mt-1 max-w-2xl text-sm text-slate-400">
				Instantánea de nodos, heartbeats y pares dirigidos reportados al coordinador.
			</p>
		</div>

		<button
			type="button"
			onclick={() => void refresh(true)}
			disabled={busy}
			aria-busy={refreshing}
			class="inline-flex w-fit items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-emerald-500/40 hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.8"
				stroke-linecap="round"
				stroke-linejoin="round"
				class={['size-4', refreshing && 'animate-spin']}
				aria-hidden="true"
			>
				<path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
			</svg>
			{refreshing ? 'Actualizando…' : 'Actualizar ahora'}
		</button>
	</div>

	<StatusBar {dashboard} {error} {lastSuccess} refreshMs={REFRESH_MS} />

	{#if dashboard}
		<NodeTable nodes={dashboard.nodes} pairs={dashboard.status.pairs} {offlineAfterS} />

		<PairTable pairs={dashboard.status.pairs} {previousPairs} {offlineAfterS} {asOfMs} />
	{:else}
		<section
			class="rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 px-6 py-12 text-center"
			aria-live="polite"
		>
			<p
				class="mx-auto grid size-12 place-items-center rounded-full border border-slate-700 bg-slate-900 text-slate-400"
				aria-hidden="true"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.6"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-6"
				>
					<circle cx="12" cy="12" r="9" />
					<path d="M12 7v5l3 2" />
				</svg>
			</p>
			<h3 class="mt-4 text-lg font-semibold text-slate-100">Esperando datos del backend</h3>
			<p class="mx-auto mt-2 max-w-xl text-sm text-slate-400">
				Todavía no hay una instantánea válida del coordinador. El panel sigue consultando cada 5 s y
				mostrará los nodos en cuanto el backend responda.
			</p>
			{#if error}
				<p class="mx-auto mt-3 max-w-xl text-xs break-words text-rose-300/80">{error}</p>
			{/if}
		</section>
	{/if}
</div>
