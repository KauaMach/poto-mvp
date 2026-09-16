/// <reference types="vite/client" />

/* Variáveis de ambiente do build. Declaradas para que um nome errado seja erro
 * de tipo em vez de `undefined` silencioso em produção. */
interface ImportMetaEnv {
  /** Identificação deste totem, gravada no chamado. Ver `comum/api.ts`. */
  readonly VITE_POTO_TOTEM_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
