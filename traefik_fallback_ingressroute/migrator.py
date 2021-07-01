"""
This module is used for migrating Traefik v1 ingresses
over to Traefik v2 ingressroutes.
"""

import json
import logging
import os
import subprocess  # nosec
from typing import Any, Dict, List, Optional

import yaml


class IngressMigrator:
    # pylint: disable=no-else-return
    # pylint: disable=fixme
    # Or else mypy will complain about a 'Missing return statement'
    """
    A class that represent a IngressMigrator
    """

    def __init__(
        self, generate_new_spec: bool = True, level: int = logging.INFO
    ) -> None:
        """
        Class constructor.
        :param level: The log level. Default: logging.INFO
         :param generate_new_spec: Call the k8s cluster again and do a new export
        of ingresses.
        """
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=level
        )
        self.log_level: int = level
        self.generate_new_spec = generate_new_spec

    def _get_traefik_v1_ingress_spec(self) -> list:
        """
        Get all ingresses and return a list with all the specifications in JSON format.
        :return: list
        """
        if self.generate_new_spec:
            os.environ.get("KUBECONFIG")
            command: str = "kubectl get ingress -A -o json"
            command_list: list = command.split(" ")
            with open("ingresses.json.tmp", "w") as out_file:
                subprocess.run(command_list, stdout=out_file, check=True)  # nosec
        with open("ingresses.json.tmp") as json_file:
            data: dict = json.load(json_file)
            items: Optional[List] = data.get("items")
        if items is not None:
            return items
        else:
            return []

    @staticmethod
    def _get_service_entry(backend: Optional[Dict], namespace: str) -> dict:
        """
        Get the service details for the IngressRoute as a dict

        :param backend: The backend spec for the current Ingress.
        :param namespace: The namespace containing the current Ingress.
        :return: dict
        """
        service_entry: dict = {}
        if backend is not None:
            service: Optional[Dict] = backend.get("service")
            if service is not None:
                svc_name: Optional[Any] = service.get("name")
                port: Optional[Dict] = service.get("port")
                if port is not None:
                    svc_port: Optional[Any] = port.get("number")
                    if svc_port is None:
                        svc_port = port.get("name")
                    service_entry = {
                        "kind": "Service",
                        "name": svc_name,
                        "namespace": namespace,
                        "port": svc_port,
                    }
        return service_entry

    @staticmethod
    def _get_rule_match(path: dict, host: str) -> str:
        """
        Calculate the match expression in the IngressRoute rule
        :param path: A path branch in the Ingress spec (if it exist).
        :param host: The hostname mentioned in the Ingress rule.
        :return: str
        """
        uri = path.get("path", "NO_PATH_KEY")
        _host_match: str = ""
        if host == "NO_HOST_KEY":
            _host_match = "HostRegexp(`{domain:.+}`)"
        else:
            _host_match = f"Host(`{host}`)"
        _path_match: str = ""
        if uri == "NO_PATH_KEY":
            pass
        elif uri == "/":
            _path_match = "Path(`/`)"
        else:
            _path_match = f"PathPrefix(`{uri}`)"
        if uri == "NO_PATH_KEY":
            return _host_match
        else:
            return f"{_host_match} && {_path_match}"

    def _get_routes(
        self, name: str, namespace: str, rules: list, priority: int = 2
    ) -> list:
        # pylint: disable=no-else-return
        """
        Get all possible routes for the new ingressroute definition
        :param name: The name of the ingress.
        :param namespace: The namespace that the ingress is running in.
        :param rules: The current ingress rules.
        :param priority: What priority should this ingressroute rule have. Default: 2
        :return: list
        """
        routes: list = []
        rule: dict
        for rule in rules:
            host: Optional[Any] = rule.get("host", "NO_HOST_KEY")
            http: Optional[Any] = rule.get("http")
            if http is not None:
                paths: Optional[List] = http.get("paths")
                if paths is not None:
                    path: dict
                    for path in paths:
                        route: dict = {"kind": "Rule"}
                        backend: Optional[Dict] = path.get("backend")
                        rule_match: str = self._get_rule_match(path, str(host))
                        if rule_match:
                            route["match"] = rule_match
                        route["middlewares"] = [{"name": f"{name}-mw"}]
                        route["priority"] = priority
                        service_entry: dict = self._get_service_entry(
                            backend, namespace
                        )
                        if service_entry:
                            route["services"] = [service_entry]
                        routes.append(route)
        return routes

    @staticmethod
    def _get_middleware(name: str, rules: list) -> dict:
        """
        Generates a JSON payload that can be used to create a Traefik v2 Middleware
        custom resource.
        :param name: The name of a current Ingress.
        :param rules: The rules for a current Ingress.
        :return: dict
        """
        prefixes = []
        for rule in rules:
            rule_with_hints: dict = rule
            http: Optional[Dict] = rule_with_hints.get("http")
            if http is not None:
                paths: Optional[List] = http.get("paths")
                if paths is not None:
                    for path in paths:
                        uri: str = path.get("path")
                        prefixes.append(uri)
        middleware: dict = {
            "apiVersion": "traefik.containo.us/v1alpha1",
            "kind": "Middleware",
            "metadata": {"name": f"{name}-mw", "namespace": "kube-system"},
            "spec": {"stripPrefix": {"prefixes": prefixes}},
        }
        return middleware

    def get_all_middlewares(self):
        """
        Generates a temporary JSON file that can be used to create
        Traefik v2 Middleware custom resources for all Ingresses.
        """
        items: list = self._get_traefik_v1_ingress_spec()
        for item in items:
            metadata: dict = item.get("metadata")
            spec: dict = item.get("spec")
            name: Optional[Any] = metadata.get("name")
            rules: Optional[List] = spec.get("rules")
            if rules is not None:
                self._get_middleware(str(name), rules)

    def get_fallback_ingressroute(self) -> None:
        """
        Generates a temporary JSON file that can be used to create one IngressRoute
        from all Ingresses.
        """
        routes: list = []
        items: list = self._get_traefik_v1_ingress_spec()
        for item in items:
            metadata: dict = item.get("metadata")
            spec: dict = item.get("spec")
            name: Optional[Any] = metadata.get("name")
            namespace: Optional[Any] = metadata.get("namespace", "default")
            rules: Optional[List] = spec.get("rules")
            if rules is not None:
                routes.append(self._get_routes(str(name), str(namespace), rules))
        flat_list = [entry for sublist in routes for entry in sublist]
        fallback: dict = {
            "apiVersion": "traefik.containo.us/v1alpha1",
            "kind": "IngressRoute",
            "metadata": {"name": "traefik-v1-fallback", "namespace": "kube-system"},
            "spec": {"entryPoints": ["web"], "routes": flat_list},
        }
        print(fallback)
        with open("ingressroute.json.tmp", "w") as json_file:
            json.dump(fallback, json_file, indent=4, sort_keys=True)
        with open("ingressroute.yaml.tmp", "w") as yaml_file:
            yaml.dump(fallback, yaml_file)
