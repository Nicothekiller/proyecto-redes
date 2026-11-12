<script lang="ts">
	import type { Dashboard } from '#lib/types.ts';
	import { formatDateTime } from '#lib/format.ts';

	interface Props {
		dashboard: Dashboard | null;
		error: string | null;
		lastSuccess: string | null;
		refreshMs: number;
	}

	let { dashboard, error, lastSuccess, refreshMs }: Props = $props();

	const nodesTotal = $derived(dashboard?.nodes.length ?? 0);
	const heartbeatRecent = $derived(
		dashboard?.nodes.filter((node) => node.heartbeat_recent).length ?? 0
	);
	const provenPairs = $derived(
		dashboard?.status.pairs.filter((pair) => pair.connectivity_proven).length ?? 0
	);
	const pairsTotal = $derived(dashboard?.status.pairs.length ?? 0);
	const refreshSeconds = $derived(Math.round(refreshMs / 1000));
	const asOf = $derived(dashboard?.status.as_of ?? null);
	const hasProvenPair = $derived(provenPairs > 0);
</script>

{#snippet metric(label: string, value: string, hint: string, number: string)}
	<div
		class="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_4px_16px_-8px_rgba(15,23,42,0.12)] sm:p-6"
	>
		<div class="flex items-center justify-between gap-3">
			<p class="text-sm font-medium text-slate-600">{label}</p>
			<span
				aria-hidden="true"
				class="grid size-9 place-items-center rounded-xl bg-blue-50 font-mono text-xs font-semibold text-blue-700"
				>{number}</span
			>
		</div>
		<p class="mt-4 text-3xl leading-tight font-semibold tracking-tight text-slate-900 tabular-nums">
			{value}
		</p>
		<p class="mt-2 text-xs leading-relaxed text-slate-500">{hint}</p>
	</div>
{/snippet}

<section class="space-y-4" aria-label="Resumen del estado del overlay">
	<div class="grid gap-3 sm:grid-cols-3">
		{@render metric(
			'Nodos registrados',
			String(nodesTotal),
			'presentes en el registro de coordinación',
			'01'
		)}
		{@render metric(
			'Heartbeat reciente',
			`${heartbeatRecent} / ${nodesTotal}`,
			'con señal dentro de la ventana del servidor',
			'02'
		)}
		{@render metric(
			'Al menos un par probado',
			hasProvenPair ? 'sí' : 'no',
			`${provenPairs} de ${pairsTotal} pares dirigidos con conectividad probada`,
			'03'
		)}
	</div>
	<div class="flex flex-wrap gap-x-6 gap-y-2 px-1 text-xs text-slate-500">
		<span>Instantánea: {formatDateTime(asOf)}</span>
		<span>Última consulta: {formatDateTime(lastSuccess)}</span>
		<span>Actualización cada {refreshSeconds} s</span>
	</div>

	{#if error}
		<div
			role="alert"
			class="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-rose-800"
		>
			<p class="text-sm font-semibold text-rose-800">Error al consultar el backend</p>
			<p class="mt-1 text-sm break-words">{error}</p>
			<p class="mt-1 text-xs text-rose-700">
				{#if lastSuccess}
					Se conserva la última instantánea correcta, obtenida el {formatDateTime(lastSuccess)}. El
					panel seguirá reintentando.
				{:else}
					Todavía no hay una instantánea correcta. El panel seguirá reintentando.
				{/if}
			</p>
		</div>
	{/if}
</section>
