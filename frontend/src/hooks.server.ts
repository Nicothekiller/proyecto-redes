import { SESSION_COOKIE, validSession } from '#lib/server/auth.ts';
import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit/hooks';

export const handle: Handle = async ({ event, resolve }) => {
	const route = event.route.id;
	if (
		(route === '/' || route === '/api/dashboard') &&
		!validSession(event.cookies.get(SESSION_COOKIE))
	) {
		if (route === '/api/dashboard') {
			return Response.json({ error: 'inicia sesión para acceder al dashboard' }, { status: 401 });
		}
		redirect(303, '/login');
	}
	return resolve(event);
};
