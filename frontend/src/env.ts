import { building } from '$app/env';
import { defineEnvVars } from '@sveltejs/kit/env';

function requiredAtRuntime(value: string | undefined): string {
	if (value === undefined && !building) {
		throw new Error('API_KEY is required at runtime');
	}
	return value ?? '';
}

export const variables = defineEnvVars({
	API_BASE_URL: {
		description: 'Base URL of the FastAPI coordination server',
		schema: (value) => value ?? 'http://127.0.0.1:8000'
	},
	API_KEY: {
		description: 'Bearer key used by the SvelteKit server to query FastAPI',
		schema: requiredAtRuntime
	}
});
