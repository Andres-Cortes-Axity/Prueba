import { ImicroService } from "./interface";
import micro from "../../models/micro.model";


/**
 * @export
 * @implements {ImicroModelService}
 */
const microService: ImicroService = {
    /**
     * @returns {Promise < any[] >}
     * @memberof microFacade
     */
    async findAll(): Promise<any[]> {
        // Para enviar un mensaje a kafka
        // await Kafka.send("test", 'Hello');
        return micro.findAll();
    }
}

export default microService;