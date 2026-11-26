// 전자식 차일드락 제어 SW CI 파이프라인
// 실행 환경: Jenkins 2.580.2 (172.16.7.122:80), Windows 11 내장 노드, 서비스 계정 LocalSystem
// Python 3.12·3.13은 PYTHON_ROOT 아래 설치본을 사용한다 (설치 경로가 바뀌면 이 값만 수정)
pipeline {
    agent any

    options {
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PYTHON_ROOT = 'C:\\Users\\user\\AppData\\Local\\Programs\\Python'
        PYTHONIOENCODING = 'utf-8'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }

    stages {
        stage('품질 게이트') {
            matrix {
                axes {
                    axis {
                        name 'PYVER'
                        values 'Python312', 'Python313'
                    }
                }
                stages {
                    stage('환경 준비') {
                        steps {
                            bat '''
                                "%PYTHON_ROOT%\\%PYVER%\\python.exe" -m venv .venv-%PYVER%
                                .venv-%PYVER%\\Scripts\\python.exe -m pip install -q pytest pytest-cov ruff fastapi httpx
                            '''
                        }
                    }
                    stage('정적 분석 (Ruff)') {
                        steps {
                            bat '''
                                .venv-%PYVER%\\Scripts\\python.exe -m ruff check --no-cache .
                                .venv-%PYVER%\\Scripts\\python.exe -m ruff format --no-cache --check .
                            '''
                        }
                    }
                    stage('단위 시험 (branch 커버리지 100%)') {
                        steps {
                            // 두 Python 셀이 같은 작업 공간에서 병렬 실행되므로 커버리지 파일을 분리한다
                            bat '''
                                set COVERAGE_FILE=.coverage-%PYVER%
                                .venv-%PYVER%\\Scripts\\python.exe -m pytest -p no:cacheprovider -W error ^
                                    --cov --cov-branch --cov-fail-under=100 ^
                                    --junitxml=reports\\junit-%PYVER%.xml ^
                                    --cov-report=xml:reports\\coverage-%PYVER%.xml
                            '''
                        }
                    }
                    stage('함수 길이·주석률') {
                        steps {
                            bat '''
                                if exist src (
                                    .venv-%PYVER%\\Scripts\\python.exe -m tools.check_quality tools src
                                ) else (
                                    .venv-%PYVER%\\Scripts\\python.exe -m tools.check_quality tools
                                )
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit-*.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
        }
    }
}
