# DarkSpace
![Team Logo](static/img/logo.png)
**DarkSpace** is a fantastic web application that is an improved version of the original NYU Brightspace, with convenient integration of GitHub Repositories and a user-friendly interface.

## Project Description

Our Project is deployed on Digital Ocean and is accessible at [DarkSpace](https://darkspace-f66yb.ondigitalocean.app/).

### Team: tung-tung-sahur
- [Jiaxi Zhang](https://github.com/SuQichen777)
- [Yilei Weng](https://github.com/ShadderD)
- [Yuquan Hu](https://github.com/N-A-E-S)
- [Henry Yu](https://github.com/ky2389)
![Team Logo](static/img/loader.png)

### Features
Our design inspiration comes from our experience with NYU Brightspace. We had interviews with our professor and combined our own experiences to create a more user-friendly and efficient system.

- **User Authentication**: Users can register, log in, and manage their profiles. Only users with special permissions can register as instructors.
- **GitHub Integration**: Users can link their GitHub accounts and repositories to the application. Interaction between teachers and students about assignments or contents can be done with selection of files from the GitHub repository.
- **Chat System**: Users can chat with each other in an inner chat system.
- **Email Notifications**: Users receive email notifications for new assignments, deadlines, and submissions.

## Project Setup

### Docker Images

### Run Our Application
1. Clone the repository:
   ```bash
   git clone https://github.com/software-students-spring2025/5-final-tung-tung-sahur
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

3. Open your web browser and navigate to `127.0.0.1:3000` or `localhost:3000` to access the application.

4. If you want to enter the mongodb shell manually, you can do so by running:
    ```bash
    docker exec -it mongodb mongosh
    ```
5. When you are done, you can stop the containers by running:
    ```bash
    docker compose down
    ```
    Or

    ```bash
    docker-compose down
    ```
    Using whichever command is available on your system.

