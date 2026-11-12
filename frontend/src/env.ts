import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	API_BASE_URL: {
		description: 'Base URL of the FastAPI coordination server',
		schema: (value) => value ?? 'http://127.0.0.1:8000'
	}
});
