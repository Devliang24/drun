# 🔗 CI/CD 集成

本文档汇总了常见平台的最小可用示例，帮助你将 Drun 接入流水线。

提示：建议将敏感配置（如 `BASE_URL`、账号密码、API Key）放入平台的 Secret/变量管理，并通过 `.env` 或环境变量方式传入。

## GitHub Actions

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: pip install -e .

      - name: Run Tests
        env:
          BASE_URL: ${{ secrets.API_BASE_URL }}
          USER_USERNAME: ${{ secrets.TEST_USERNAME }}
          USER_PASSWORD: ${{ secrets.TEST_PASSWORD }}
        run: |
          drun run testcases \
            --html reports/report.html \
            --report reports/run.json \
            --mask-secrets \
            --notify-only failed

      - name: Upload Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-report
          path: reports/report.html
```

## GitLab CI

```yaml
stages:
  - test

api-tests:
  stage: test
  image: python:3.10
  before_script:
    - pip install -e .
  script:
    - |
      drun run testcases \
        --html reports/report.html \
        --report reports/run.json \
        --mask-secrets \
        --notify-only failed
  artifacts:
    when: always
    paths:
      - reports/
  variables:
    BASE_URL: $API_BASE_URL
    USER_USERNAME: $TEST_USERNAME
    USER_PASSWORD: $TEST_PASSWORD
```

## Jenkins（Declarative Pipeline）

```groovy
pipeline {
  agent any
  environment {
    BASE_URL = credentials('BASE_URL')
  }
  stages {
    stage('Setup') {
      steps {
        sh 'python3 -m pip install -U pip && pip install -e .'
        sh 'echo "BASE_URL=${BASE_URL}" > .env'
        sh 'mkdir -p reports'
      }
    }
    stage('Run') {
      steps {
        sh 'drun run testcases --html reports/report.html --report reports/run.json --mask-secrets'
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'reports/**', fingerprint: true
    }
  }
}
```

## 最佳实践

1. 环境隔离：为 dev/staging/prod 分别提供 `.env` 或环境变量
2. 掩码输出：流水线使用 `--mask-secrets`，避免泄露敏感数据
3. 失败通知：结合 `--notify` 与 `--notify-only failed`
4. 报告归档：将 HTML/JSON 报告保存为制品，便于回溯
5. 标签策略：用 `-k` 拆分 smoke、regression 分层回归

