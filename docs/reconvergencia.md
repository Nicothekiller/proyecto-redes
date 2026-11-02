# Reconvergencia ante cambio de endpoint

Tiempo desde que un nodo cambia de IP o de puerto hasta que el ping por el overlay vuelve a ser estable. Criterio del #12: el tráfico se recupera en ~2 polls (20 s).

## Resultados

Poll de 10 s, chequeo local de endpoint cada 1 s, keepalive de 25 s. 10 repeticiones por caso.

| Caso | Media | Mediana | Mín | Máx | Sin recuperar |
|---|---|---|---|---|---|
| a cambia de IP, b le hace ping | 0,95 s | 1,05 s | 0,05 s | 1,06 s | 0 |
| a y b cambian de IP a la vez | 11,47 s | 11,11 s | 2,06 s | 17,06 s | 0 |
| a cambia de puerto, b le hace ping | 1,06 s | 1,06 s | 1,05 s | 1,06 s | 0 |

## Por qué dan esos tiempos

**Si se mueve un solo nodo, no hace falta esperar el poll.** El nodo que se movió detecta el cambio en menos de 1 s y hace un tick inmediato. Ese tick envía el ping de probe por el túnel, y WireGuard en el otro extremo aprende la dirección nueva del primer paquete autenticado (roaming). Por eso el tiempo queda cerca de 1 s.

**Si se mueven los dos, el servidor es indispensable.** Cada uno envía a la dirección vieja del otro, así que el roaming no puede arrancar. La recuperación depende de que uno lea en `/peers` la dirección nueva del otro. Ambos reportan su cambio en el primer segundo, pero el otro puede haber leído `/peers` justo antes, y entonces espera su siguiente poll. De ahí el rango de 2 a 17 s, siempre por debajo de 2 polls. Bajar el intervalo reduciría este tiempo a cambio de más tráfico hacia el servidor.

## Método

- WireGuard de kernel en contenedores Docker, 1 servidor y 2 clientes en una LAN `172.30.0.0/24`.
- El cambio se forzó de verdad: `ip addr flush` más `ip addr add` para la IP, `wg set wg0 listen-port` para el puerto.
- El cambio y la medición arrancan en el mismo instante absoluto, tomado del reloj común de los contenedores. El resultado va hasta el primer ping de una racha de 5 seguidos.
- El tiempo entre repeticiones es aleatorio (3 a 12 s), para que el cambio caiga en una fase cualquiera del poll.

## Límites

- La resolución es de ~1 s, porque cada ping fallido espera 1 s. El 1,05 s repetido refleja esa espera, no una precisión de centésimas.
- Es un banco en contenedores, sin pérdida ni latencia de una red real. Falta repetirlo en el hotspot con máquinas físicas (M5).
- El banco usado todavía no está en el repo; entra con el #13.
