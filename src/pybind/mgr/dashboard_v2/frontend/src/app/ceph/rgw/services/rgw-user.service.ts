import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';

import * as _ from 'lodash';

@Injectable()
export class RgwUserService {

  private url = '/api/rgw/proxy/user';

  constructor(private http: HttpClient) { }

  list() {
    return this.http.get('/api/rgw/proxy/metadata/user')
      .toPromise()
      .then((userIds: Array<string>) => {
        // Now get the detailed information per user ID.
        const promises = [];
        _.forEach(userIds, (uid) => {
          const promise = this.get(uid);
          promises.push(promise);
        });
        return Promise.all(promises)
          .then((resp: Array<object>) => {
            return resp;
          });
      });
  }

  get(uid: string) {
    let params = new HttpParams();
    params = params.append('uid', uid);
    return this.http.get(this.url, { params: params })
      .toPromise()
      .then((resp: object) => {
        return resp;
      });
  }

  getQuota(uid: string) {
    let params = new HttpParams();
    params = params.append('quota', '');
    params = params.append('uid', uid);
    return this.http.get(this.url, { params: params })
      .toPromise()
      .then((resp: any) => {
        return resp;
      });
  }
}
