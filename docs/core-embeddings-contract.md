# Contrato de laboratorio de embeddings con `comunito/core`

Esta interfaz prepara la segunda fase sin copiar credenciales, fotografías ni embeddings reales a este repositorio.

## Requisitos del laboratorio

- El módulo de generación, versionado y administración vive en `comunito/core`.
- El acceso inicial se limita a usuarios con rol `superadmin`.
- Cada lote debe declarar `schema_version`, `model`, `dimension`, `generated_at` y un identificador estable de persona.
- La exportación consumida por FacialV3 es CSV autenticado o un endpoint equivalente; nunca se almacenan tokens en Git.

## Fila mínima consumida por FacialV3

```text
person_id,name,embedding,active
```

El campo `embedding` puede ser un arreglo JSON o una lista separada por comas. FacialV3 lo normaliza y mantiene una caché local atómica para seguir operando si la conexión falla.

## Pendiente de la fase `core`

La implementación del laboratorio y su rama separada debe hacerse en `github.com/comunito/core`, con autorización de superadministrador y pruebas de exportación sintética. Esta rama no realiza esa modificación porque el repositorio de trabajo solicitado para esta etapa es exclusivamente `github.com/comunito/FacialV3`.
