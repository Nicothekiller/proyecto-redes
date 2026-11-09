import { getDashboard } from '#lib/server/backend.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ setHeaders }) => {
	setHeaders({ 'cache-control': 'no-store' });

	try {
		return {
			dashboard: await getDashboard(),
			error: null
		};
	} catch (error) {
		return {
			dashboard: null,
			error: error instanceof Error ? error.message : 'no se pudo cargar el dashboard'
		};
	}
};
