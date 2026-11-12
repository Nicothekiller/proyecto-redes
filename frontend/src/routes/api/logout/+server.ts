import { SESSION_COOKIE, sameOrigin } from '#lib/server/auth.ts';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = ({ request, cookies }) => {
	if (!sameOrigin(request)) return new Response(null, { status: 403 });
	cookies.delete(SESSION_COOKIE, { path: '/' });
	return new Response(null, { status: 204 });
};
