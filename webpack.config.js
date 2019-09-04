const path = require('path');

module.exports = {
  mode: "development",
  entry: './code.js',
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'dist')
  },
  node: {
    "fs": "empty"
  }
}
