import { BackendError, getDashboard } from '#lib/server/backend.ts';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	try {
		return Response.json(await getDashboard(), {
			headers: { 'cache-control': 'no-store' }
		});
	} catch (error) {
		const message = error instanceof BackendError ? error.message : 'error consultando el backend';
		return Response.json(
			{ error: message },
			{
				status: 502,
				headers: { 'cache-control': 'no-store' }
			}
		);
	}
};
