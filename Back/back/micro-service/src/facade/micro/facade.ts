import { microService } from "../../services";
import { ImicroFacade } from "./interface";


/**
 * @export
 * @implements {ImicroModelService}
 */
const microFacade: ImicroFacade = {
    /**
     * @returns {Promise < any[] >}
     * @memberof microFacade
     */
    async findAll(): Promise<any[]> {

        let micro = await microService.findAll();
        return micro;
    }
}

export default microFacade;