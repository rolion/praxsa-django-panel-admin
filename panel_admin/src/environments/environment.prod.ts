// Build de produccion servido por el nginx del stack v2 en /panel/, en el mismo
// origen que la API (/product/...): apiUrl vacio = URLs relativas, asi no se
// hornea ningun dominio (ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento).
export const environment = {
    production: true,
    apiUrl: '',
    // Numero de WhatsApp de la consulta de la calculadora (global; valor inicial
    // tomado de proforma/, pendiente de confirmar con negocio).
    whatsappNumber: '+59178181012',
  };
