import { getDashboard } from '#lib/server/backend.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ setHeaders, locals }) => {
	setHeaders({ 'cache-control': 'no-store' });

	try {
		return {
			dashboard: await getDashboard(locals.key),
			role: locals.role,
			error: null
		};
	} catch (error) {
		return {
			dashboard: null,
			role: locals.role,
			error: error instanceof Error ? error.message : 'no se pudo cargar el dashboard'
		};
	}
};
