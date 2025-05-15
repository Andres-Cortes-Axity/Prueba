import { createLogger, transports, format, level } from "winston";
const { combine, timestamp, prettyPrint } = format;
import { LogData, ElasticsearchTransport } from 'winston-elasticsearch';
import elasticsearchTemplate from './elasticLogTemplate';
import esFormat from './elasticFormat';
import config from '../../config/env';

// Set ELASTICSEARCH_URLS to a list of URLs to connect to, e.g. "http://elasticsearch:9200".


// winston-elasticsearch automatically moves a bunch of the log data into
// a field called "meta".  This undoes this and moves it all back...
function esTransformer({ message, level, timestamp, meta }: LogData) {
    return { message, level, timestamp, ...meta };
}

const esTransport = new ElasticsearchTransport({
    transformer: esTransformer,
    clientOpts: {
        node:
            config.elasticSearch.HOST,
        auth: {
            username: config.elasticSearch.USER,
            password: config.elasticSearch.PASSWORD,
        },
        log: level
    } as any,
    indexPrefix: `log-${process.env.NODE_ENV}-${config.elasticSearch.INDEX_LOGGER}`,
    indexTemplate: elasticsearchTemplate,
    ensureIndexTemplate: true,
    format: esFormat(),
})



export const logger = createLogger({
    transports: [new transports.Console(), esTransport],
    format: combine(
        format.splat(),
        format.metadata(),
        prettyPrint(),
        timestamp(),
        format.printf(({ timestamp, level, message, metadata }) => {
            return `[${timestamp}] [micro-service] -> ${level}: ${message}`;
        })
    ),
});
