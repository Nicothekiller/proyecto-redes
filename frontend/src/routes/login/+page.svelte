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

<section
	class="mx-auto mt-4 max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-[0_12px_36px_-16px_rgba(15,23,42,0.2)] sm:mt-12 sm:p-9"
>
	<div
		class="mb-6 grid size-12 place-items-center rounded-2xl bg-blue-50 text-blue-700"
		aria-hidden="true"
	>
		<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" class="size-6"
			><rect x="5" y="10" width="14" height="10" rx="2" /><path
				d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2"
			/></svg
		>
	</div>
	<p class="mb-2 text-xs font-semibold tracking-[0.16em] text-blue-700 uppercase">headscale-lite</p>
	<h2 class="text-2xl font-semibold tracking-tight text-slate-900">Acceso al dashboard</h2>
	<p class="mt-2 text-sm leading-relaxed text-slate-600">
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
			class="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 focus:outline-none"
		/>
		{#if error}
			<p role="alert" class="text-sm text-rose-700">{error}</p>
		{/if}
		<button
			type="submit"
			disabled={busy}
			class="w-full rounded-xl bg-blue-700 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-800 disabled:opacity-60"
		>
			Entrar
		</button>
	</form>
</section>
