variable "TAG" {
  default = "latest"
}

variable "DOCKER_REGISTRY" {
  default = "ghcr.io/transfer-enigma"
}

group "default" {
  targets = ["python-apps", "db-migration", "reverseproxy"]
}

target "python-apps" {
  context = "./Python/"
  target = "python-apps"
  tags = ["${DOCKER_REGISTRY}/calculator-python-apps:${TAG}"]
}

target "db-migration" {
  context = "./Python/"
  target = "db-migration"
  tags = ["${DOCKER_REGISTRY}/calculator-db-migration:${TAG}"]
}

target "frontend-builder" {
  context = "./Node/"
  target = "frontend-builder"
}

target "frontadmin-builder" {
  context = "./Node/"
  dockerfile = "Dockerfile"
  target = "frontadmin-builder"
}

target "reverseproxy" {
  context = "."
  target = "reverseproxy"
  tags = ["${DOCKER_REGISTRY}/calculator-reverseproxy:${TAG}"]
  contexts = {
    frontend-builder = "target:frontend-builder",
    frontadmin-builder = "target:frontadmin-builder"
  }
}
