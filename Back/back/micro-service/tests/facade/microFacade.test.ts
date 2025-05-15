process.env.NODE_ENV = 'test'

import { expect } from "chai";
import microFacade from '../../src/facade/micro/facade';
import { db } from '../../src/config/connection/database';
import micro from "../../src/models/micro.model";


describe('microFacade Test', () => {

    before('Init', async() => {
        await db.sync({ force: true});
        micro.create({
        id: 1,
        name: 'test',
        createdAt: '2020-01-01',
        updatedAt: '2020-01-01'
        });

        //Para lanzar pruebas con kafka
        // let topics = [
        //     'pruebas',
        //     'test'
        // ];
        // try{
        //     await Kafka.init(topics);
        //     console.log('Connected to Kafka');

        // }catch(err){
        //     console.log('Error', err);
        // }
    });
  
    describe('FindAll', () => {
        it('should return one user', async () => {
            const micro: any[] = await microFacade.findAll();
            expect(1).equal(micro.length);
        });
    });
});