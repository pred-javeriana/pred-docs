# ADR-02-005: Asignación de Recursos y Poda con ASHA

- **Fecha:** 2026-08-31
- **Estado:** Aceptada

## **Contexto & Problema**

El algoritmo TPE genera nuevas propuestas de hiperparámetros informadas por evaluaciones previas. Sin embargo, TPE no asigna recursos computacionales ni aborta configuraciones deficientes. Se necesita un mecanismo para descartar hiperparámetros malos a tiempo, comunicándose con el *GreedyRunner*.

## **Opciones Consideradas**

- **Option A:** Poda determinista (Successive Halving simple). Probar todas las configuraciones en la ventana 1, ordenar, podar la mitad inferior y avanzar la mitad superior a la ventana 2 de forma síncrona.
- *Pros:* Lógica de control sencilla.
- *Cons:* Cuello de botella. Los *workers* rápidos se quedan ociosos esperando a que el modelo más pesado termine de evaluar su ventana.
- **Option B:** Asynchronous Successive Halving (ASHA). Un mecanismo donde cada *worker* solicita métricas parciales al *GreedyRunner* y decide podar asincrónicamente comparando contra las métricas ya registradas, requiriendo un mínimo de 4 ventanas antes de descartar para evitar sesgos por ruido.
- *Pros:* Eficiencia de cómputo maximizada, crucial para despliegues escalables o en la nube.
- *Cons:* Obliga a implementar una capa de almacenamiento del registro (registro compartido) para que los *workers* comparen sus métricas.

## **Decisión**

Se adopta la **Option B**. ASHA se implementará como la estrategia de poda y asignación de recursos, operando como el único componente autorizado para enviar la señal de "descarte" basándose en el payload tipado que recibe del *runner* temporal.

## **Consecuencias**

### **Positivas**

- Garantiza que el cómputo se dedique exclusivamente a las configuraciones predictivas más prometedoras.

### **Negativas**

- Se debe programar explícitamente el control de excepciones para la regla de las 4 ventanas de gracia.
