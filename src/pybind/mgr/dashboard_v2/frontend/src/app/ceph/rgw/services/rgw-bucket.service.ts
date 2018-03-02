import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';

import * as _ from 'lodash';

@Injectable()
export class RgwBucketService {

  private url = '/api/rgw/proxy/bucket';

  constructor(private http: HttpClient) { }

  list() {
    return this.http.get(this.url)
      .toPromise()
      .then((buckets: Array<string>) => {
        // Now get the detailed information per bucket.
        const promises = [];
        _.forEach(buckets, (bucket) => {
          const promise = this.get(bucket);
          promises.push(promise);
        });
        return Promise.all(promises)
          .then((resp: Array<object>) => {
            return resp;
          });
      });
  }

  get(bucket: string) {
    let params = new HttpParams();
    params = params.append('bucket', bucket);
    return this.http.get(`${this.url}/get`, { params: params })
      .toPromise()
      .then((resp: object) => {
        return resp;
      });
  }

  create(bucket: string, uid: string) {
    let params = new HttpParams();
    params = params.append('bucket', bucket);
    params = params.append('uid', uid);
    return this.http.put(`${this.url}/create`, { params: params })
      .toPromise()
      .then((resp: any) => {
        return resp;
      });
  }

  set(bucket: string, bucketId: string, uid: string) {
    let params = new HttpParams();
    params = params.append('bucket', bucket);
    params = params.append('bucket-id', bucketId as string);
    params = params.append('uid', uid);
    return this.http.put(this.url, { params: params })
      .toPromise()
      .then((resp: any) => {
        return resp;
      });
  }

  delete(bucket: string, purgeObjects = true) {
    let params = new HttpParams();
    params = params.append('bucket', bucket);
    params = params.append('purge-objects', purgeObjects ? 'true' : 'false');
    return this.http.delete(`${this.url}/delete`, { params: params })
      .toPromise()
      .then((resp: any) => {
        return resp;
      });
  }

  query(bucket: string) {
    let params = new HttpParams();
    params = params.append('bucket', bucket);
    return this.http.get(this.url, { params: params })
      .toPromise()
      .then((resp: HttpResponse<string>) => {
        // Make sure we have received valid data.
        if (!_.isString(resp.body)) {
          return [];
        }
        if (resp.status !== 200) {
          return resp.body;
        }
        // Return an array to be able to support wildcard searching someday.
        return [resp.body];
      });
  }
}
