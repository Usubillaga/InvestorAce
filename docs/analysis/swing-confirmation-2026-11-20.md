# InvestorAce · prueba retrospectiva de la doble confirmación

**Conclusión.** La evidencia disponible permite comprobar la ejecución de la regla en simulación. No demuestra una mejora de rentabilidad o riesgo. El histórico comparable contiene 11 sesiones y el filtro nuevo no cambió ninguna orden frente a Opportunity + Timing.

| Variante | Compras señaladas | Compras ejecutadas | Ventas ejecutadas | Rendimiento acumulado en EUR |
|---|---:|---:|---:|---:|
| Opportunity sin filtro técnico | 8 | 8 | 0 | +2,90 % |
| Opportunity + Timing anterior | 4 | 4 | 1 | −1,12 % |
| Swing con doble confirmación | 4 | 4 | 1 | −1,12 % |

Ventana de sesiones del 4 al 18 de noviembre de 2026. Se verificaron 117 builds y 53 contenían la versión v18.1. Nueve sesiones tenían un mercado en tendencia alcista según el informe. El rendimiento incluye las posiciones abiertas a su última valoración verificada. No se anualizó el resultado ni se estimó una tasa de acierto. Ninguna variante tuvo sesiones con huecos de valoración en esta ventana.

La regla nueva exige un puntaje fundamental de al menos 7, un puntaje Opportunity de al menos 7 y una etiqueta Buy o Strong Buy. También requiere S&P 500 por encima de su media de 200 sesiones, acción por encima de sus medias de 36, 50 y 200 sesiones y una extensión de 0 a 3 ATR. Solo se comparan entradas largas en acciones.

La simulación usa el primer build verificable de cada sesión elegible. Las etiquetas, medias y contexto de mercado provienen de las observaciones archivadas en ese momento. Los precios de ejecución y EUR/USD provienen de una serie archivada posterior, cortada en cada sesión disponible. Se aplican los costes del modelo (0,10 % por ejecución) y el cierre posterior a la decisión. La serie de precios puede incorporar revisiones del proveedor. El programa no usa datos de valoración posteriores para reconstruir señales antiguas.

Para decidir si el filtro aporta valor harían falta más sesiones prospectivas, más operaciones cerradas, mercados de distinta tendencia y costes de ejecución observados. El backtest técnico plurianual de v1.5/v1.6 evalúa otras reglas.

```sh
python swing_backtest.py --through-build 20261119T192608260099-db83c3744c0d42cf897129503b5d060b
```
