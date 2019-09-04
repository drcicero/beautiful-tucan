const path = require('path');

module.exports = {
  mode: "development",
  entry: './src/code.js',
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'dist')
  },
  node: {
    "fs": "empty"
  }
}
