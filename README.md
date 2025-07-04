# Experimental MCP server for OpenRelik

1. Create a new user, e.g. `agent-smith` (using admin.py)
2. Create an API key for `agent-smith` (via logging in as the user and create one in the UI)
3. Make sure to give `agent-smith` access to folders you want to expose

4. Update docker-compose.yml

```
  openrelik-mcp-server:
    container_name: openrelik-mcp-server
    build:
      context: ./openrelik-mcp-server
      dockerfile: ./docker/Dockerfile
    ports:
      - "8081:8081"
    environment:
      - OPENRELIK_API_URL=http://openrelik-server:8710
      - OPENRELIK_API_KEY=<OPENRELIK API KEY>
````
