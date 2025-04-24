# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

### Run Our Application
1. Clone the repository:
   ```bash
   git clone
   ```
   and navigate to the project directory.

2. Build the Docker images and start the containers:
    ```bash
    docker compose up --build
    ``` 
    Or

    ```bash
    docker-compose up --build
    ```
    Using whichever command is available on your system.

3. If you want to enter the mongodb shell manually, you can do so by running:
    ```bash
    docker exec -it mongodb mongosh
    ```

   `
