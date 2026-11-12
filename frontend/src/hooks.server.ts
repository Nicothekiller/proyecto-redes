import { SESSION_COOKIE } from '#lib/server/auth.ts';
import { BackendError, getRole } from '#lib/server/backend.ts';
import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit/hooks';

export const handle: Handle = async ({ event, resolve }) => {
	const route = event.route.id;
	if (route === '/' || route?.startsWith('/api/dashboard')) {
		const key = event.cookies.get(SESSION_COOKIE);
		if (key) {
			try {
				event.locals.role = await getRole(key);
				event.locals.key = key;
				return resolve(event);
			} catch (error) {
				if (!(error instanceof BackendError) || error.status !== 401) {
					return new Response('No se pudo contactar al backend', { status: 502 });
				}
			}
		}
		if (route.startsWith('/api/'))
			return Response.json({ error: 'inicia sesión' }, { status: 401 });
		redirect(303, '/login');
	}
	return resolve(event);
};
