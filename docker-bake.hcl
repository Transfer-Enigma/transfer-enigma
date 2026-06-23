variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["python-apps", "db-migration", "reverseproxy", "scheduler"]
}

target "python-apps" {
  context = "./Python/"
  target = "python-apps"
  tags = ["danielgreen1806/calculator-python-apps:${TAG}"]
}

target "scheduler" {
  context = "./Python/"
  target = "scheduler"
  tags = ["danielgreen1806/calculator-scheduler:${TAG}"]
}

target "db-migration" {
  context = "./Python/"
  target = "db-migration"
  tags = ["danielgreen1806/calculator-db-migration:${TAG}"]
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
  tags = ["danielgreen1806/calculator-reverseproxy:${TAG}"]
  contexts = {
    frontend-builder = "target:frontend-builder",
    frontadmin-builder = "target:frontadmin-builder"
  }
}
