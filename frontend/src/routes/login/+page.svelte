<script lang="ts">
	let key = $state('');
	let error = $state('');
	let busy = $state(false);

	async function login(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		try {
			const response = await fetch('/api/login', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ key })
			});
			if (response.ok) {
				window.location.assign('/');
			} else {
				error = response.status === 401 ? 'Clave incorrecta' : 'No se pudo iniciar sesión';
			}
		} catch {
			error = 'No se pudo contactar al servidor';
		} finally {
			key = '';
			busy = false;
		}
	}
</script>

<section class="mx-auto max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
	<h2 class="text-xl font-semibold text-slate-50">Acceso al dashboard</h2>
	<p class="mt-2 text-sm text-slate-400">Introduce la clave del dashboard para continuar.</p>
	<form method="POST" onsubmit={login} class="mt-6 space-y-4">
		<label for="key" class="block text-sm font-medium text-slate-200">Clave del dashboard</label>
		<input
			id="key"
			name="key"
			bind:value={key}
			type="password"
			required
			autocomplete="current-password"
			class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 focus:border-emerald-400 focus:outline-none"
		/>
		{#if error}
			<p role="alert" class="text-sm text-rose-400">{error}</p>
		{/if}
		<button
			type="submit"
			disabled={busy}
			class="rounded-lg bg-emerald-500 px-4 py-2 font-medium text-slate-950 hover:bg-emerald-400"
		>
			Entrar
		</button>
	</form>
</section>
