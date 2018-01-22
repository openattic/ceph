# Ceph Dashboard

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 1.6.3.

## CherryPy server

Run `ng build` to generate the dist files that CherryPy will serve.
Navigate to `http://localhost:8080`.

## Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The app will automatically reload if you change any of the source files.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory. Use the `-prod` flag for a production build.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via [Protractor](http://www.protractortest.org/).

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI README](https://github.com/angular/angular-cli/blob/master/README.md).

## Examples of generator

```
# Create module 'Core'
src/app> ng generate module core -m=app --routing

# Create module 'Auth' under module 'Core'
src/app/core> ng generate module auth -m=core --routing
or, alternatively:
src/app> ng generate module core/auth -m=core --routing

# Create component 'Login' under module 'Auth'
src/app/core/auth> ng generate component login -m=core/auth
or, alternatively:
src/app> ng generate component core/auth/login -m=core/auth
```
