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
	let activeTab = $state<'nodes' | 'pairs'>('nodes');

	function tabKeydown(event: KeyboardEvent) {
		if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
		event.preventDefault();
		activeTab =
			event.key === 'Home'
				? 'nodes'
				: event.key === 'End'
					? 'pairs'
					: activeTab === 'nodes'
						? 'pairs'
						: 'nodes';
		document.getElementById(`tab-${activeTab}`)?.focus();
	}

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

<div class="space-y-8">
	<div class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
		<div>
			<p class="mb-2 text-xs font-semibold tracking-[0.16em] text-blue-700 uppercase">
				Panel de control
			</p>
			<h2 class="text-3xl font-semibold tracking-tight text-slate-900">Estado de la red</h2>
			<p class="mt-2 text-sm text-slate-500">Un vistazo a los nodos y conexiones del overlay.</p>
		</div>

		<button
			type="button"
			onclick={() => void refresh(true)}
			disabled={busy}
			aria-busy={refreshing}
			class="inline-flex w-fit items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
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
		<div>
			<div class="mb-3 flex flex-col gap-1">
				<h3 class="text-lg font-semibold tracking-tight text-slate-900">Detalle de la red</h3>
				<p class="text-sm text-slate-500">
					Consulta los dispositivos registrados y sus conexiones.
				</p>
			</div>
			<div role="tablist" aria-label="Datos de la red" class="flex gap-6 border-b border-slate-200">
				{#each [{ id: 'nodes', label: 'Nodos', count: dashboard.nodes.length }, { id: 'pairs', label: 'Pares', count: dashboard.status.pairs.length }] as tab (tab.id)}
					<button
						id={`tab-${tab.id}`}
						type="button"
						role="tab"
						aria-selected={activeTab === tab.id}
						aria-controls={`panel-${tab.id}`}
						tabindex={activeTab === tab.id ? 0 : -1}
						onclick={() => (activeTab = tab.id as 'nodes' | 'pairs')}
						onkeydown={tabKeydown}
						class={[
							'-mb-px border-b-2 px-1 py-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-blue-600',
							activeTab === tab.id
								? 'border-blue-600 text-blue-700'
								: 'border-transparent text-slate-500 hover:text-slate-800'
						]}
					>
						{tab.label}
						<span class="ml-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600"
							>{tab.count}</span
						>
					</button>
				{/each}
			</div>
			<div
				id="panel-nodes"
				role="tabpanel"
				tabindex="0"
				aria-labelledby="tab-nodes"
				hidden={activeTab !== 'nodes'}
				class="pt-5"
			>
				{#if activeTab === 'nodes'}
					<NodeTable
						nodes={dashboard.nodes}
						pairs={dashboard.status.pairs}
						{offlineAfterS}
						admin={data.role === 'admin'}
						ondeleted={() => void refresh()}
					/>
				{/if}
			</div>
			<div
				id="panel-pairs"
				role="tabpanel"
				tabindex="0"
				aria-labelledby="tab-pairs"
				hidden={activeTab !== 'pairs'}
				class="pt-5"
			>
				{#if activeTab === 'pairs'}
					<PairTable pairs={dashboard.status.pairs} {previousPairs} {offlineAfterS} {asOfMs} />
				{/if}
			</div>
		</div>
	{:else}
		<section
			class="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center"
			aria-live="polite"
		>
			<p
				class="mx-auto grid size-12 place-items-center rounded-full border border-slate-200 bg-white text-slate-500"
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
			<h3 class="mt-4 text-lg font-semibold text-slate-900">Esperando datos del backend</h3>
			<p class="mx-auto mt-2 max-w-xl text-sm text-slate-600">
				Todavía no hay una instantánea válida del coordinador. El panel sigue consultando cada 5 s y
				mostrará los nodos en cuanto el backend responda.
			</p>
			{#if error}
				<p class="mx-auto mt-3 max-w-xl text-xs break-words text-rose-700">{error}</p>
			{/if}
		</section>
	{/if}
</div>
