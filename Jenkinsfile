pipeline {
 agent {
docker { 
            image 'python:3.11-slim' 
        }
 }
 
triggers {
                githubPush()
}

 stages {
 stage('Execute Automation Script') {
 steps {
 echo 'Running the specified validation script from TimePass ...'
 sh '''
  pip install pytest 

 mkdir -p reports
 python -m pytest tests/ --junitxml=reports/test_results.xml
 '''
 
 }
 }
 }

//post {

//always {

//junit  allowEmptyResults: true, testResults: 'reports/test_results.xml'


//mail bcc: '', body: '\'Check the results here: ${BUILD_URL}\'', cc: '', from: '', replyTo: '', subject: 'TimePass test script  execution result', to: 'msmsinghchauhan@gmail.com'

//}

//}

}


