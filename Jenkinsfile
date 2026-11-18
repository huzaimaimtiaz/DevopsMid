pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
    }

    triggers {
        githubPush()
    }

    environment {
        STUDENT_ID = 'FA23-BDS-017'
        IMAGE      = 'midterm-fa23-bds-017'
        CONTAINER  = 'midterm-app'
        VENV       = '.venv-ci'
        NOTIFY_TO  = 'qasimalik@gmail.com'
    }

    stages {
        stage('Fetch latest data') {
            steps {
                checkout scm
                sh '''
                    git log -1 --pretty="Commit %h by %an: %s"
                    echo "Dataset lines (incl. header): $(wc -l < dataset/train.csv)"
                '''
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
                    "$VENV/bin/pip" install -q -r requirements.txt
                    "$VENV/bin/pip" freeze > requirements.lock
                '''
            }
        }

        stage('Retrain model') {
            steps {
                sh '''
                    export GIT_COMMIT=$(git rev-parse HEAD)
                    "$VENV/bin/python" train.py
                '''
            }
        }

        stage('Run tests') {
            steps {
                sh '"$VENV/bin/python" -m unittest discover -s tests -v'
            }
        }

        stage('Build Docker image') {
            steps {
                sh 'docker build -t $IMAGE:$BUILD_NUMBER -t $IMAGE:latest .'
            }
        }

        stage('Deploy on EC2') {
            steps {
                sh '''
                    docker rm -f $CONTAINER 2>/dev/null || true
                    docker run -d --name $CONTAINER --restart unless-stopped \
                        -p 8000:8000 $IMAGE:$BUILD_NUMBER
                '''
            }
        }

        stage('Smoke test live API') {
            steps {
                sh '''
                    EXPECTED=$("$VENV/bin/python" -c "import json;print(json.load(open('artifacts/metrics.json'))['model_version'])")
                    for i in $(seq 1 30); do
                        curl -fs http://localhost:8000/metrics -o live.json && break
                        sleep 2
                    done
                    cat live.json; echo
                    grep -q "$EXPECTED" live.json
                    curl -fs -X POST http://localhost:8000/predict \
                        -H 'Content-Type: application/json' \
                        -d '{"records":[{"voltage_drift":1.2,"thermal_load":0.5,"supply_variance":-0.3,"demand_spike":0.8}]}'
                    echo
                '''
            }
        }
    }

    post {
        success {
            sh '''
                docker images $IMAGE --format '{{.Tag}}' | grep -vx -e latest -e "$BUILD_NUMBER" \
                    | xargs -r -I{} docker rmi $IMAGE:{} || true
                docker image prune -f || true
            '''
        }
        always {
            script {
                def m = fileExists('artifacts/metrics.json') ? readFile('artifacts/metrics.json') : 'metrics.json not produced'
                emailext(
                    to: env.NOTIFY_TO,
                    subject: "${env.STUDENT_ID} - MIDTERM-${env.STUDENT_ID} build #${env.BUILD_NUMBER}: ${currentBuild.currentResult}",
                    mimeType: 'text/plain',
                    body: """Student Reg No: ${env.STUDENT_ID}
Job: ${env.JOB_NAME}
Build: #${env.BUILD_NUMBER}
Result: ${currentBuild.currentResult}
Commit: ${env.GIT_COMMIT}
Build URL: ${env.BUILD_URL}

Model metrics:
${m}
"""
                )
            }
        }
    }
}
