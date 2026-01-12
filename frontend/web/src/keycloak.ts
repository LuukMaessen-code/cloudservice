import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: "http://localhost:8080",
  realm: "demo-chat",
  clientId: "cloudservice-gateway",
});

export default keycloak;
