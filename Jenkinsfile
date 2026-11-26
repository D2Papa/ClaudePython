// 전자식 차일드락 제어 SW CI 파이프라인
// 전제: Linux 에이전트에 python3.12, python3.13이 설치되어 있음 (미확인 — 서버 환경 확인 필요)
pipeline {
    agent any

    options {
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
    }

    stages {
        stage('품질 게이트') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON'
                        values 'python3.12', 'python3.13'
                    }
                }
                stages {
                    stage('환경 준비') {
                        steps {
                            sh '''
                                ${PYTHON} -m venv .venv-${PYTHON}
                                .venv-${PYTHON}/bin/pip install -q "pytest>=8" "pytest-cov>=5" "ruff>=0.6"
                            '''
                        }
                    }
                    stage('정적 분석 (Ruff)') {
                        steps {
                            sh '''
                                .venv-${PYTHON}/bin/ruff check .
                                .venv-${PYTHON}/bin/ruff format --check .
                            '''
                        }
                    }
                    stage('단위 테스트 (branch 커버리지 100%)') {
                        steps {
                            sh '''
                                .venv-${PYTHON}/bin/python -m pytest -W error \
                                    --cov --cov-branch --cov-fail-under=100 \
                                    --junitxml=reports/junit-${PYTHON}.xml \
                                    --cov-report=xml:reports/coverage-${PYTHON}.xml
                            '''
                        }
                    }
                    stage('함수 길이·주석률') {
                        steps {
                            sh '.venv-${PYTHON}/bin/python -m tools.check_quality tools $(test -d src && echo src)'
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
