"""
This module is used for migrating Traefik v1 ingresses
over to Traefik v2 ingressroutes.
"""
from traefik_fallback_ingressroute.migrator import IngressMigrator

if __name__ == "__main__":
    ingress_migrator: IngressMigrator = IngressMigrator()
    ingress_migrator.get_fallback_ingressroute()
