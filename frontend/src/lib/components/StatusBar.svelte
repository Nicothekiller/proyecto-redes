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

{#snippet metric(label: string, value: string, hint: string)}
	<div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
		<p class="text-[0.65rem] font-medium tracking-[0.15em] text-slate-500 uppercase">{label}</p>
		<p class="mt-2 text-base leading-tight font-semibold text-slate-100 tabular-nums">{value}</p>
		<p class="mt-1 text-xs text-slate-500">{hint}</p>
	</div>
{/snippet}

<section class="space-y-4" aria-label="Resumen del estado del overlay">
	<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
		{@render metric(
			'Nodos registrados',
			String(nodesTotal),
			'presentes en el registro de coordinación'
		)}
		{@render metric(
			'Heartbeat reciente',
			`${heartbeatRecent} / ${nodesTotal}`,
			'con señal dentro de la ventana del servidor'
		)}
		{@render metric(
			'al menos un par probado',
			hasProvenPair ? 'sí' : 'no',
			`${provenPairs} de ${pairsTotal} pares dirigidos con conectividad probada`
		)}
		{@render metric('as_of del servidor', formatDateTime(asOf), 'instante de la instantánea')}
		{@render metric(
			'Última consulta correcta',
			formatDateTime(lastSuccess),
			`refresco automático cada ${refreshSeconds} s`
		)}
	</div>

	<div
		class="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6"
	>
		<span class="text-[0.65rem] font-medium tracking-[0.15em] text-slate-500 uppercase"
			>Leyenda</span
		>
		<span class="inline-flex items-center gap-2 text-xs text-slate-300">
			<span aria-hidden="true" class="size-2.5 shrink-0 rounded-full bg-slate-400"></span>
			Registrado
			<span class="text-slate-500">— nodo dado de alta en el coordinador</span>
		</span>
		<span class="inline-flex items-center gap-2 text-xs text-slate-300">
			<span aria-hidden="true" class="size-2.5 shrink-0 rounded-full bg-sky-400"></span>
			Heartbeat reciente
			<span class="text-slate-500">— señal vista dentro de la ventana</span>
		</span>
		<span class="inline-flex items-center gap-2 text-xs text-slate-300">
			<span aria-hidden="true" class="size-2.5 shrink-0 rounded-full bg-emerald-400"></span>
			Conectividad probada
			<span class="text-slate-500">— al menos un par dirigido probado</span>
		</span>
	</div>

	{#if error}
		<div
			role="alert"
			class="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-rose-100"
		>
			<p class="text-sm font-semibold text-rose-200">Error al consultar el backend</p>
			<p class="mt-1 text-sm break-words">{error}</p>
			<p class="mt-1 text-xs text-rose-200/70">
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
