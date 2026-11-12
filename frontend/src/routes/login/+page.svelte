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

<section class="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-6">
	<h2 class="text-xl font-semibold text-slate-900">Acceso al dashboard</h2>
	<p class="mt-2 text-sm text-slate-600">
		Introduce la clave de lectura o de administrador para continuar.
	</p>
	<form method="POST" onsubmit={login} class="mt-6 space-y-4">
		<label for="key" class="block text-sm font-medium text-slate-700">Clave de acceso</label>
		<input
			id="key"
			name="key"
			bind:value={key}
			type="password"
			required
			autocomplete="current-password"
			class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 focus:border-emerald-400 focus:outline-none"
		/>
		{#if error}
			<p role="alert" class="text-sm text-rose-700">{error}</p>
		{/if}
		<button
			type="submit"
			disabled={busy}
			class="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
		>
			Entrar
		</button>
	</form>
</section>
