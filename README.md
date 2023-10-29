# ExampleFlaskApp

## Install Necessary Packages

In ExampleFlaskApp folder
```
source venv/bin/activate

brew install node
npm install --save axios
```

In ExampleFlaskApp/frontend folder
```
export NODE_OPTIONS=--openssl-legacy-provider
export REACT_APP_API_URL=http://localhost:8080/api

npm start
```

In ExampleFlaskApp/backend folder
```
brew install docker (or install from Docker website)
docker build -t sample-backend .
docker run -p 8080:8080 sample-backend
```