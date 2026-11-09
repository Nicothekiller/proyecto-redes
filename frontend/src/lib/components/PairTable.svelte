<script lang="ts">
	import type { Pair } from '#lib/types.ts';
	import {
		clampAge,
		formatAge,
		formatBytes,
		formatDateTime,
		formatDelta,
		formatRtt,
		isStale,
		pairKey
	} from '#lib/format.ts';

	interface Props {
		pairs: Pair[];
		previousPairs: Pair[];
		offlineAfterS: number;
		asOfMs: number;
	}

	let { pairs, previousPairs, offlineAfterS, asOfMs }: Props = $props();

	const previousByKey = $derived.by(() => {
		const byKey: Record<string, Pair> = {};
		for (const pair of previousPairs) {
			byKey[pairKey(pair.reporter, pair.peer)] = pair;
		}
		return byKey;
	});

	function shortId(nodeId: string): string {
		return nodeId.length > 10 ? `${nodeId.slice(0, 8)}…` : nodeId;
	}
</script>

<section class="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
	<div class="overflow-x-auto">
		<table class="w-full min-w-[72rem] border-collapse text-left text-sm">
			<caption class="border-b border-slate-800 px-4 py-3 text-left">
				<span class="text-sm font-semibold text-slate-100">Pares dirigidos reportados</span>
				<span class="ml-2 text-xs text-slate-500">
					{pairs.length} reportes · «Δ» compara con la instantánea anterior
				</span>
			</caption>
			<thead class="bg-slate-900/80 text-xs tracking-wider text-slate-500 uppercase">
				<tr>
					<th scope="col" class="px-4 py-3 font-medium">Reportero → par</th>
					<th scope="col" class="px-4 py-3 font-medium">Endpoint</th>
					<th scope="col" class="px-4 py-3 font-medium">Handshake</th>
					<th scope="col" class="px-4 py-3 font-medium">Tráfico rx / tx</th>
					<th scope="col" class="px-4 py-3 font-medium">Sonda</th>
					<th scope="col" class="px-4 py-3 font-medium">Conectividad probada</th>
					<th scope="col" class="px-4 py-3 font-medium">Reportado</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-800">
				{#if pairs.length === 0}
					<tr>
						<td colspan="7" class="px-4 py-10 text-center text-sm text-slate-500">
							Sin datos de pares por ahora. Aparecerán cuando los clientes reporten sus vecinos y el
							coordinador reciba sus métricas.
						</td>
					</tr>
				{:else}
					{#each pairs as pair (pairKey(pair.reporter, pair.peer))}
						{@const key = pairKey(pair.reporter, pair.peer)}
						{@const previous = previousByKey[key]}
						{@const stale = isStale(pair.reported_at, asOfMs, offlineAfterS)}
						<tr
							class={[
								'transition-colors hover:bg-slate-800/40',
								stale && 'bg-slate-950/40 opacity-50'
							]}
						>
							<td class="px-4 py-3">
								<div class="flex items-center gap-2 font-mono text-xs whitespace-nowrap">
									<span class="text-slate-100">{pair.reporter_overlay_ip}</span>
									<span aria-hidden="true" class="text-slate-600">→</span>
									<span class="text-slate-300">{pair.peer_overlay_ip}</span>
								</div>
								<p class="mt-1 text-[0.65rem] text-slate-500">
									{shortId(pair.reporter)} → {shortId(pair.peer)}
								</p>
							</td>
							<td class="px-4 py-3 font-mono text-xs text-slate-400">
								{pair.endpoint ?? '—'}
							</td>
							<td
								class="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-300 tabular-nums"
								title="edad del último handshake"
							>
								{formatAge(clampAge(pair.handshake_age_s))}
							</td>
							<td class="px-4 py-3">
								<dl class="space-y-1 font-mono text-xs whitespace-nowrap tabular-nums">
									<div class="flex items-baseline gap-2">
										<dt class="w-5 text-slate-500">rx</dt>
										<dd class="text-slate-200">{formatBytes(pair.rx_bytes)}</dd>
										<dd class="text-[0.65rem] text-emerald-400/80">
											Δ {formatDelta(pair.rx_bytes, previous?.rx_bytes)}
										</dd>
									</div>
									<div class="flex items-baseline gap-2">
										<dt class="w-5 text-slate-500">tx</dt>
										<dd class="text-slate-200">{formatBytes(pair.tx_bytes)}</dd>
										<dd class="text-[0.65rem] text-emerald-400/80">
											Δ {formatDelta(pair.tx_bytes, previous?.tx_bytes)}
										</dd>
									</div>
								</dl>
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								<div class="flex flex-col gap-1">
									{#if pair.probe_ok === null}
										<span
											class="inline-flex w-fit items-center gap-1.5 rounded-full bg-slate-800 px-2 py-0.5 text-[0.65rem] font-medium text-slate-400 ring-1 ring-slate-700 ring-inset"
										>
											<span aria-hidden="true" class="size-1.5 rounded-full bg-slate-600"></span>
											sin sonda
										</span>
									{:else if pair.probe_ok}
										<span
											class="inline-flex w-fit items-center gap-1.5 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-medium text-emerald-300 ring-1 ring-emerald-500/30 ring-inset"
										>
											<span aria-hidden="true" class="size-1.5 rounded-full bg-emerald-400"></span>
											ok
										</span>
									{:else}
										<span
											class="inline-flex w-fit items-center gap-1.5 rounded-full bg-rose-500/15 px-2 py-0.5 text-[0.65rem] font-medium text-rose-300 ring-1 ring-rose-500/30 ring-inset"
										>
											<span aria-hidden="true" class="size-1.5 rounded-full bg-rose-400"></span>
											fallo
										</span>
									{/if}
									<span class="font-mono text-xs text-slate-300 tabular-nums">
										RTT {formatRtt(pair.probe_rtt_ms)}
									</span>
									<span class="text-[0.65rem] text-slate-500">
										{formatDateTime(pair.probe_ran_at)}
									</span>
								</div>
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								{#if pair.connectivity_proven}
									<span
										class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-medium text-emerald-300 ring-1 ring-emerald-500/30 ring-inset"
									>
										<span aria-hidden="true" class="size-1.5 rounded-full bg-emerald-400"></span>
										probada
									</span>
								{:else}
									<span
										class="inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-2 py-0.5 text-[0.65rem] font-medium text-slate-400 ring-1 ring-slate-700 ring-inset"
									>
										<span aria-hidden="true" class="size-1.5 rounded-full bg-slate-600"></span>
										sin probar
									</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-xs whitespace-nowrap">
								<span class="text-slate-300">{formatDateTime(pair.reported_at)}</span>
								{#if stale}
									<span
										class="mt-1 block w-fit rounded-full bg-amber-500/10 px-2 py-0.5 text-[0.65rem] font-medium text-amber-300 ring-1 ring-amber-500/30 ring-inset"
										title={`sin reportes dentro de ${offlineAfterS} s`}
									>
										desactualizado
									</span>
								{/if}
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
	<p class="border-t border-slate-800 px-4 py-3 text-xs text-slate-500">
		Cada fila es un reporte dirigido <span class="text-slate-400">reportero → par</span>. Las filas
		atenuadas superan la ventana de frescura del servidor ({offlineAfterS} s).
	</p>
</section>
