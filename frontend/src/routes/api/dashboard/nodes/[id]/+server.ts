import { sameOrigin } from '#lib/server/auth.ts';
import { BackendError, deleteNode, getDashboard } from '#lib/server/backend.ts';
import type { RequestHandler } from './$types';

export const DELETE: RequestHandler = async ({ request, locals, params }) => {
	if (!sameOrigin(request)) return new Response(null, { status: 403 });
	if (locals.role !== 'admin')
		return Response.json({ error: 'requiere acceso de administrador' }, { status: 403 });
	try {
		const dashboard = await getDashboard(locals.key);
		const node = dashboard.nodes.find((item) => item.node_id === params.id);
		if (!node) return Response.json({ error: 'nodo no encontrado' }, { status: 404 });
		if (node.heartbeat_recent)
			return Response.json({ error: 'el nodo está conectado' }, { status: 409 });
		await deleteNode(locals.key, params.id);
		return new Response(null, { status: 204 });
	} catch (error) {
		const status = error instanceof BackendError && error.status === 404 ? 404 : 502;
		return Response.json({ error: 'no se pudo eliminar el nodo' }, { status });
	}
};
