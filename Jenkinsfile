pipeline {
 agent any
triggers {
                githubPush()
}

 stages {
 stage('Execute Automation Script') {
 steps {
 echo 'Running the specified validation script from TimePass ...'
 
 
 sh '''
 apt-get update || apt-get update
 apt-get install -y python3 python3-pip || apt-get install -y python3 python3-pip
 pip3 install pytest --break-system-packages || pip3 install pytest

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


