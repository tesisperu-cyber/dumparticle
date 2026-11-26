"""SciELO Kernel — adaptador DESACTIVADO por diseño.
No se documentó/verificó aún una ruta oficial de Kernel accesible públicamente; para no
inventar endpoints, este módulo solo declara la interfaz. Se implementará cuando se
confirme la ruta con documentación oficial y una llamada real (ver docs/LIMITACIONES.md).
Nota: el PID de ArticleMeta (p.ej. S0034-89102014000200001) NO es intercambiable con el
identificador de documento de Kernel (scielo-id)."""


class KernelNotConfigured(NotImplementedError):
    pass


class KernelClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

    def get_document_manifest(self, scielo_id: str):
        raise KernelNotConfigured("Kernel no verificado/configurado; use ArticleMeta (xmlrsps).")
