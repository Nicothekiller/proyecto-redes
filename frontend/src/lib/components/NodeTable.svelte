<script lang="ts">
	import type { Node, Pair } from '#lib/types.ts';
	import { formatAge, formatDateTime, truncatePubkey } from '#lib/format.ts';

	interface Props {
		nodes: Node[];
		pairs: Pair[];
		offlineAfterS: number;
		admin: boolean;
		ondeleted: () => void;
	}

	let { nodes, pairs, offlineAfterS, admin, ondeleted }: Props = $props();
	let deleting = $state<string | null>(null);
	let deleteError = $state('');

	async function removeNode(node: Node) {
		if (node.heartbeat_recent || deleting) return;
		if (
			!confirm(
				`¿Eliminar el nodo ${node.overlay_ip} (${node.node_id})? Asegúrate de que su interfaz WireGuard esté apagada. Su IP podrá reutilizarse inmediatamente.`
			)
		)
			return;
		deleting = node.node_id;
		deleteError = '';
		try {
			const response = await fetch(`/api/dashboard/nodes/${encodeURIComponent(node.node_id)}`, {
				method: 'DELETE',
				headers: { 'content-type': 'application/json' }
			});
			if (!response.ok) {
				const result = await response.json();
				deleteError = result.error ?? 'No se pudo eliminar el nodo';
				return;
			}
			ondeleted();
		} catch {
			deleteError = 'No se pudo contactar al servidor';
		} finally {
			deleting = null;
		}
	}

	const registeredPeers = $derived(Math.max(0, nodes.length - 1));

	const provenPeers = $derived.by(() => {
		const peersByNode: Record<string, string[]> = {};

		function add(node: string, peer: string) {
			const peers = (peersByNode[node] ??= []);
			if (!peers.includes(peer)) peers.push(peer);
		}

		for (const pair of pairs) {
			if (!pair.connectivity_proven) continue;
			add(pair.reporter, pair.peer);
			add(pair.peer, pair.reporter);
		}

		return peersByNode;
	});

	function shortId(nodeId: string): string {
		return nodeId.length > 10 ? `${nodeId.slice(0, 8)}…` : nodeId;
	}
</script>

<section
	class="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_4px_16px_-8px_rgba(15,23,42,0.12)]"
>
	{#if deleteError}<p
			role="alert"
			class="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
		>
			{deleteError}
		</p>{/if}
	<div class="overflow-x-auto">
		<table class="w-full min-w-[80rem] border-collapse text-left text-sm">
			<caption class="border-b border-slate-100 px-5 py-4 text-left">
				<span class="text-sm font-semibold text-slate-900">Nodos registrados</span>
				<span class="ml-2 text-xs text-slate-500">
					{nodes.length} en el registro · «conectividad probada» = al menos un par dirigido
				</span>
			</caption>
			<thead class="bg-slate-50/80 text-xs tracking-wider text-slate-500 uppercase">
				<tr>
					<th scope="col" class="px-4 py-3 font-medium">IP overlay</th>
					<th scope="col" class="px-4 py-3 font-medium">Nodo</th>
					<th scope="col" class="px-4 py-3 font-medium">Clave pública</th>
					<th scope="col" class="px-4 py-3 font-medium">Endpoint</th>
					<th scope="col" class="px-4 py-3 font-medium">Heartbeat reciente</th>
					<th scope="col" class="px-4 py-3 font-medium">Pares registrados</th>
					<th scope="col" class="px-4 py-3 font-medium">Pares probados</th>
					<th scope="col" class="px-4 py-3 font-medium">Registrado</th>
					<th scope="col" class="px-4 py-3 font-medium">Conectividad probada</th>
					{#if admin}<th scope="col" class="px-4 py-3 font-medium">Acciones</th>{/if}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-100">
				{#if nodes.length === 0}
					<tr>
						<td colspan={admin ? 10 : 9} class="px-4 py-10 text-center text-sm text-slate-500">
							Sin nodos registrados todavía. El panel se actualizará cuando un cliente haga
							<i>join</i> y envíe su primer heartbeat.
						</td>
					</tr>
				{:else}
					{#each nodes as node (node.node_id)}
						{@const proven = provenPeers[node.node_id]?.length ?? 0}
						<tr
							class={[
								'transition-colors hover:bg-slate-50',
								!node.heartbeat_recent && 'bg-slate-50'
							]}
						>
							<td class="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-900">
								{node.overlay_ip}
							</td>
							<td class="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-700">
								<span title={node.node_id}>{shortId(node.node_id)}</span>
							</td>
							<td class="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-700">
								<span title={node.pubkey}>{truncatePubkey(node.pubkey)}</span>
							</td>
							<td class="px-4 py-3 font-mono text-xs text-slate-600">
								{node.endpoint || '—'}
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								<div class="flex flex-col gap-1">
									<span
										class="font-mono text-xs text-slate-700 tabular-nums"
										title={`último heartbeat: ${formatDateTime(node.last_heartbeat)}`}
									>
										{formatAge(node.heartbeat_age_s)}
									</span>
									<span
										class={[
											'inline-flex w-fit items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.65rem] font-medium ring-1 ring-inset',
											node.heartbeat_recent
												? 'bg-sky-500/15 text-sky-700 ring-sky-500/30'
												: 'bg-slate-100 text-slate-600 ring-slate-200'
										]}
									>
										<span
											aria-hidden="true"
											class={[
												'size-1.5 rounded-full',
												node.heartbeat_recent ? 'bg-sky-400' : 'bg-slate-500'
											]}
										></span>
										{node.heartbeat_recent ? 'reciente' : 'vencido'}
									</span>
									{#if !node.heartbeat_recent}
										<span class="text-[0.65rem] text-slate-500">
											sin señal en {offlineAfterS} s
										</span>
									{/if}
								</div>
							</td>
							<td class="px-4 py-3 font-mono text-xs text-slate-700 tabular-nums">
								{registeredPeers}
							</td>
							<td class="px-4 py-3 font-mono text-xs whitespace-nowrap tabular-nums">
								<span class={proven > 0 ? 'text-emerald-700' : 'text-slate-600'}>
									{proven} de {registeredPeers}
								</span>
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								<span
									class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-medium text-slate-700 ring-1 ring-slate-200 ring-inset"
								>
									<span aria-hidden="true" class="size-1.5 rounded-full bg-slate-400"></span>
									registrado
								</span>
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								{#if node.connectivity_proven}
									<span
										class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-medium text-emerald-700 ring-1 ring-emerald-500/30 ring-inset"
										title="connectivity_proven a nivel de nodo: al menos un par dirigido probado"
									>
										<span aria-hidden="true" class="size-1.5 rounded-full bg-emerald-400"></span>
										probada
									</span>
								{:else}
									<span
										class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-medium text-slate-600 ring-1 ring-slate-200 ring-inset"
										title="connectivity_proven a nivel de nodo: ningún par dirigido probado"
									>
										<span aria-hidden="true" class="size-1.5 rounded-full bg-slate-600"></span>
										sin probar
									</span>
								{/if}
							</td>
							{#if admin}
								<td class="px-4 py-3">
									<button
										type="button"
										disabled={node.heartbeat_recent || deleting !== null}
										onclick={() => removeNode(node)}
										title={node.heartbeat_recent
											? 'Solo se pueden eliminar nodos sin heartbeat reciente'
											: 'Eliminar nodo'}
										class="rounded border border-rose-200 px-3 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40"
										>{deleting === node.node_id ? 'Eliminando…' : 'Eliminar'}</button
									>
								</td>
							{/if}
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
	<p class="border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
		«Conectividad probada» a nivel de nodo se calcula como <strong
			class="font-medium text-slate-600">al menos un par</strong
		>
		dirigido probado. El detalle por par está en la tabla de pares.
	</p>
</section>
