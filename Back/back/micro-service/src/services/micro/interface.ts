
/**
 * @export
 * @interface ImicroService
 */
export interface ImicroService {

    /**
     * @returns {Promise<any[]>}
     * @memberof ImicroService
     */
    findAll(): Promise<any[]>;
}